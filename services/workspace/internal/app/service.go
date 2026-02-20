package app

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"reflect"
	"sort"
	"strings"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

const (
	invocationOutputArtifactName = "invocation-output.json"
	invocationLogsArtifactName   = "invocation-logs.jsonl"
)

type Service struct {
	workspace WorkspaceManager
	catalog   CapabilityRegistry
	policy    PolicyEngine
	tools     ToolEngine
	invStore  InvocationStore
	artifacts ArtifactStore
	audit     AuditLogger
}

func NewService(
	workspace WorkspaceManager,
	catalog CapabilityRegistry,
	policy PolicyEngine,
	tools ToolEngine,
	artifacts ArtifactStore,
	audit AuditLogger,
	invStore ...InvocationStore,
) *Service {
	resolvedInvocationStore := InvocationStore(NewInMemoryInvocationStore())
	if len(invStore) > 0 && invStore[0] != nil {
		resolvedInvocationStore = invStore[0]
	}
	return &Service{
		workspace: workspace,
		catalog:   catalog,
		policy:    policy,
		tools:     tools,
		invStore:  resolvedInvocationStore,
		artifacts: artifacts,
		audit:     audit,
	}
}

func (s *Service) CreateSession(ctx context.Context, req CreateSessionRequest) (domain.Session, *ServiceError) {
	if req.Principal.TenantID == "" {
		return domain.Session{}, invalidArgumentError("principal.tenant_id is required")
	}
	if req.Principal.ActorID == "" {
		return domain.Session{}, invalidArgumentError("principal.actor_id is required")
	}
	if req.ExpiresInSecond <= 0 {
		req.ExpiresInSecond = 3600
	}

	session, err := s.workspace.CreateSession(ctx, req)
	if err != nil {
		return domain.Session{}, internalError(err.Error())
	}
	return session, nil
}

func (s *Service) CloseSession(ctx context.Context, sessionID string) *ServiceError {
	if sessionID == "" {
		return invalidArgumentError("session_id is required")
	}
	if err := s.workspace.CloseSession(ctx, sessionID); err != nil {
		return internalError(err.Error())
	}
	return nil
}

func (s *Service) ListTools(ctx context.Context, sessionID string) ([]domain.Capability, *ServiceError) {
	session, found, err := s.workspace.GetSession(ctx, sessionID)
	if err != nil {
		return nil, internalError(err.Error())
	}
	if !found {
		return nil, notFoundError("session not found")
	}

	all := s.catalog.List()
	enabled := make([]domain.Capability, 0, len(all))
	for _, capability := range all {
		if !capabilitySupportedByRuntime(session, capability) {
			continue
		}
		decision, decisionErr := s.policy.Authorize(ctx, PolicyInput{
			Session:    session,
			Capability: capability,
			Args:       json.RawMessage("{}"),
			Approved:   true,
		})
		if decisionErr != nil {
			return nil, internalError(decisionErr.Error())
		}
		if decision.Allow {
			enabled = append(enabled, capability)
		}
	}

	sort.Slice(enabled, func(i, j int) bool {
		return enabled[i].Name < enabled[j].Name
	})
	return enabled, nil
}

func (s *Service) InvokeTool(ctx context.Context, sessionID, toolName string, req InvokeToolRequest) (domain.Invocation, *ServiceError) {
	session, found, err := s.workspace.GetSession(ctx, sessionID)
	if err != nil {
		return domain.Invocation{}, internalError(err.Error())
	}
	if !found {
		return domain.Invocation{}, notFoundError("session not found")
	}

	capability, ok := s.catalog.Get(toolName)
	if !ok {
		return domain.Invocation{}, notFoundError("tool not found")
	}

	req.CorrelationID = strings.TrimSpace(req.CorrelationID)
	if req.CorrelationID != "" {
		existing, found, serviceErr := s.findInvocationByCorrelation(ctx, sessionID, toolName, req.CorrelationID)
		if serviceErr != nil {
			return domain.Invocation{}, serviceErr
		}
		if found {
			return existing, nil
		}
	}

	invocationID := newID("inv")
	startedAt := time.Now().UTC()
	invocation := domain.Invocation{
		ID:            invocationID,
		SessionID:     sessionID,
		ToolName:      toolName,
		CorrelationID: req.CorrelationID,
		Status:        domain.InvocationStatusRunning,
		StartedAt:     startedAt,
		TraceName:     capability.Observability.TraceName,
		SpanName:      capability.Observability.SpanName,
	}
	if serviceErr := s.storeInvocation(ctx, invocation); serviceErr != nil {
		return invocation, serviceErr
	}

	if !capabilitySupportedByRuntime(session, capability) {
		invocation.Status = domain.InvocationStatusDenied
		invocation = s.finishWithError(invocation, startedAt, &domain.Error{
			Code:      ErrorCodePolicyDenied,
			Message:   unsupportedRuntimeReason(session, capability),
			Retryable: false,
		})
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		return invocation, policyDeniedError(ErrorCodePolicyDenied, unsupportedRuntimeReason(session, capability))
	}

	decision, decisionErr := s.policy.Authorize(ctx, PolicyInput{
		Session:    session,
		Capability: capability,
		Args:       req.Args,
		Approved:   req.Approved,
	})
	if decisionErr != nil {
		invocation = s.finishWithError(invocation, startedAt, &domain.Error{
			Code:      ErrorCodeInternal,
			Message:   decisionErr.Error(),
			Retryable: false,
		})
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		return invocation, internalError(decisionErr.Error())
	}
	if !decision.Allow {
		code := decision.ErrorCode
		if code == "" {
			code = ErrorCodePolicyDenied
		}
		invocation.Status = domain.InvocationStatusDenied
		invocation = s.finishWithError(invocation, startedAt, &domain.Error{
			Code:      code,
			Message:   decision.Reason,
			Retryable: false,
		})
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		return invocation, policyDeniedError(code, decision.Reason)
	}

	toolCtx := ctx
	cancel := func() {}
	if capability.Constraints.TimeoutSeconds > 0 {
		toolCtx, cancel = context.WithTimeout(ctx, time.Duration(capability.Constraints.TimeoutSeconds)*time.Second)
	}
	defer cancel()

	runResult, runErr := s.tools.Invoke(toolCtx, session, capability, req.Args)
	invocation.Output = runResult.Output
	invocation.Logs = runResult.Logs
	invocation.ExitCode = runResult.ExitCode

	artifacts, outputRef, logsRef, artifactErr := s.persistRunArtifacts(ctx, invocationID, runResult)
	if artifactErr == nil {
		invocation.Artifacts = artifacts
		invocation.OutputRef = outputRef
		invocation.LogsRef = logsRef
	}

	if runErr != nil {
		invocation = s.finishWithError(invocation, startedAt, runErr)
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		if errors.Is(toolCtx.Err(), context.DeadlineExceeded) || runErr.Code == ErrorCodeTimeout {
			return invocation, &ServiceError{
				Code:       runErr.Code,
				Message:    runErr.Message,
				HTTPStatus: 504,
			}
		}
		return invocation, &ServiceError{
			Code:       runErr.Code,
			Message:    runErr.Message,
			HTTPStatus: 500,
		}
	}

	if artifactErr != nil {
		invocation = s.finishWithError(invocation, startedAt, &domain.Error{
			Code:      ErrorCodeInternal,
			Message:   artifactErr.Error(),
			Retryable: false,
		})
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		return invocation, internalError(artifactErr.Error())
	}

	if validationErr := validateOutputAgainstSchema(capability.OutputSchema, runResult.Output); validationErr != nil {
		invocation = s.finishWithError(invocation, startedAt, &domain.Error{
			Code:      ErrorCodeInternal,
			Message:   validationErr.Error(),
			Retryable: false,
		})
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		return invocation, internalError(validationErr.Error())
	}

	endedAt := time.Now().UTC()
	invocation.Status = domain.InvocationStatusSucceeded
	invocation.CompletedAt = &endedAt
	invocation.DurationMS = endedAt.Sub(startedAt).Milliseconds()
	if serviceErr := s.storeInvocation(ctx, invocation); serviceErr != nil {
		return invocation, serviceErr
	}
	s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
	return invocation, nil
}

func (s *Service) GetInvocation(ctx context.Context, invocationID string) (domain.Invocation, *ServiceError) {
	invocation, found, err := s.invStore.Get(ctx, invocationID)
	if err != nil {
		return domain.Invocation{}, internalError(err.Error())
	}
	if !found {
		return domain.Invocation{}, notFoundError("invocation not found")
	}
	if err := s.hydrateOutputByRef(ctx, &invocation); err != nil {
		return domain.Invocation{}, internalError(err.Error())
	}
	return invocation, nil
}

func (s *Service) GetInvocationLogs(ctx context.Context, invocationID string) ([]domain.LogLine, *ServiceError) {
	invocation, serviceErr := s.GetInvocation(ctx, invocationID)
	if serviceErr != nil {
		return nil, serviceErr
	}
	if len(invocation.Logs) > 0 || invocation.LogsRef == "" {
		return invocation.Logs, nil
	}

	logs, err := s.loadLogsByRef(ctx, &invocation, invocation.LogsRef)
	if err != nil {
		return nil, internalError(err.Error())
	}
	return logs, nil
}

func (s *Service) GetInvocationArtifacts(ctx context.Context, invocationID string) ([]domain.Artifact, *ServiceError) {
	invocation, serviceErr := s.GetInvocation(ctx, invocationID)
	if serviceErr != nil {
		return nil, serviceErr
	}
	if len(invocation.Artifacts) > 0 {
		return invocation.Artifacts, nil
	}

	artifacts, err := s.artifacts.List(ctx, invocationID)
	if err != nil {
		return nil, internalError(err.Error())
	}
	return artifacts, nil
}

func (s *Service) storeInvocation(ctx context.Context, invocation domain.Invocation) *ServiceError {
	if err := s.invStore.Save(ctx, invocation); err != nil {
		return internalError(err.Error())
	}
	return nil
}

func (s *Service) finishWithError(invocation domain.Invocation, startedAt time.Time, err *domain.Error) domain.Invocation {
	endedAt := time.Now().UTC()
	if invocation.Status != domain.InvocationStatusDenied {
		invocation.Status = domain.InvocationStatusFailed
	}
	invocation.CompletedAt = &endedAt
	invocation.DurationMS = endedAt.Sub(startedAt).Milliseconds()
	invocation.Error = err
	return invocation
}

func (s *Service) findInvocationByCorrelation(
	ctx context.Context,
	sessionID string,
	toolName string,
	correlationID string,
) (domain.Invocation, bool, *ServiceError) {
	lookupStore, ok := s.invStore.(CorrelationLookupStore)
	if !ok {
		return domain.Invocation{}, false, nil
	}
	invocation, found, err := lookupStore.FindByCorrelation(ctx, sessionID, toolName, correlationID)
	if err != nil {
		return domain.Invocation{}, false, internalError(err.Error())
	}
	return invocation, found, nil
}

func (s *Service) persistRunArtifacts(
	ctx context.Context,
	invocationID string,
	runResult ToolRunResult,
) ([]domain.Artifact, string, string, error) {
	payloads, err := buildInvocationArtifactPayloads(runResult)
	if err != nil {
		return nil, "", "", err
	}
	if len(payloads) == 0 {
		return nil, "", "", nil
	}

	artifacts, err := s.artifacts.Save(ctx, invocationID, payloads)
	if err != nil {
		return nil, "", "", err
	}
	return artifacts, findArtifactIDByName(artifacts, invocationOutputArtifactName), findArtifactIDByName(artifacts, invocationLogsArtifactName), nil
}

func buildInvocationArtifactPayloads(runResult ToolRunResult) ([]ArtifactPayload, error) {
	payloads := make([]ArtifactPayload, 0, len(runResult.Artifacts)+2)
	payloads = append(payloads, runResult.Artifacts...)

	if runResult.Output != nil {
		outputData, err := json.Marshal(runResult.Output)
		if err != nil {
			return nil, fmt.Errorf("marshal invocation output artifact: %w", err)
		}
		payloads = append(payloads, ArtifactPayload{
			Name:        invocationOutputArtifactName,
			ContentType: "application/json",
			Data:        outputData,
		})
	}

	if len(runResult.Logs) > 0 {
		var logsBuffer bytes.Buffer
		encoder := json.NewEncoder(&logsBuffer)
		for _, line := range runResult.Logs {
			if err := encoder.Encode(line); err != nil {
				return nil, fmt.Errorf("marshal invocation logs artifact: %w", err)
			}
		}
		payloads = append(payloads, ArtifactPayload{
			Name:        invocationLogsArtifactName,
			ContentType: "application/x-ndjson",
			Data:        logsBuffer.Bytes(),
		})
	}

	return payloads, nil
}

func findArtifactIDByName(artifacts []domain.Artifact, name string) string {
	for _, artifact := range artifacts {
		if artifact.Name == name {
			return artifact.ID
		}
	}
	return ""
}

func (s *Service) hydrateOutputByRef(ctx context.Context, invocation *domain.Invocation) error {
	if invocation.Output != nil || strings.TrimSpace(invocation.OutputRef) == "" {
		return nil
	}
	payload, err := s.readArtifactByRef(ctx, invocation, invocation.OutputRef)
	if err != nil {
		return err
	}
	var output any
	if err := json.Unmarshal(payload, &output); err != nil {
		return fmt.Errorf("unmarshal invocation output artifact: %w", err)
	}
	invocation.Output = output
	return nil
}

func (s *Service) loadLogsByRef(ctx context.Context, invocation *domain.Invocation, logsRef string) ([]domain.LogLine, error) {
	payload, err := s.readArtifactByRef(ctx, invocation, logsRef)
	if err != nil {
		return nil, err
	}
	lines := bytes.Split(payload, []byte("\n"))
	out := make([]domain.LogLine, 0, len(lines))
	for _, line := range lines {
		if len(bytes.TrimSpace(line)) == 0 {
			continue
		}
		var item domain.LogLine
		if err := json.Unmarshal(line, &item); err != nil {
			return nil, fmt.Errorf("unmarshal invocation log line: %w", err)
		}
		out = append(out, item)
	}
	return out, nil
}

func (s *Service) readArtifactByRef(ctx context.Context, invocation *domain.Invocation, artifactID string) ([]byte, error) {
	artifact, err := s.resolveArtifact(ctx, invocation, artifactID)
	if err != nil {
		return nil, err
	}
	data, err := s.artifacts.Read(ctx, artifact.Path)
	if err != nil {
		return nil, fmt.Errorf("read artifact %s: %w", artifactID, err)
	}
	return data, nil
}

func (s *Service) resolveArtifact(ctx context.Context, invocation *domain.Invocation, artifactID string) (domain.Artifact, error) {
	for _, artifact := range invocation.Artifacts {
		if artifact.ID == artifactID {
			return artifact, nil
		}
	}
	artifacts, err := s.artifacts.List(ctx, invocation.ID)
	if err != nil {
		return domain.Artifact{}, err
	}
	invocation.Artifacts = artifacts
	for _, artifact := range artifacts {
		if artifact.ID == artifactID {
			return artifact, nil
		}
	}
	return domain.Artifact{}, fmt.Errorf("artifact ref not found: %s", artifactID)
}

type outputSchema struct {
	Type       string                          `json:"type"`
	Required   []string                        `json:"required,omitempty"`
	Properties map[string]outputSchemaProperty `json:"properties,omitempty"`
}

type outputSchemaProperty struct {
	Type string `json:"type"`
}

func validateOutputAgainstSchema(schemaRaw json.RawMessage, output any) error {
	if len(schemaRaw) == 0 || string(schemaRaw) == "null" {
		return nil
	}

	var schema outputSchema
	if err := json.Unmarshal(schemaRaw, &schema); err != nil {
		return fmt.Errorf("invalid output schema: %w", err)
	}
	if schema.Type == "" {
		return nil
	}
	if !matchesSchemaType(output, schema.Type) {
		return fmt.Errorf("tool output type mismatch: expected %s", schema.Type)
	}

	if schema.Type != "object" {
		return nil
	}
	objectValue, ok := output.(map[string]any)
	if !ok {
		return fmt.Errorf("tool output must be an object")
	}

	for _, required := range schema.Required {
		if _, exists := objectValue[required]; !exists {
			return fmt.Errorf("tool output missing required field: %s", required)
		}
	}

	for key, property := range schema.Properties {
		if property.Type == "" {
			continue
		}
		value, exists := objectValue[key]
		if !exists {
			continue
		}
		if !matchesSchemaType(value, property.Type) {
			return fmt.Errorf("tool output field %s has invalid type", key)
		}
	}
	return nil
}

func matchesSchemaType(value any, schemaType string) bool {
	switch schemaType {
	case "object":
		_, ok := value.(map[string]any)
		return ok
	case "array":
		if value == nil {
			return false
		}
		kind := reflect.TypeOf(value).Kind()
		return kind == reflect.Slice || kind == reflect.Array
	case "string":
		_, ok := value.(string)
		return ok
	case "boolean":
		_, ok := value.(bool)
		return ok
	case "integer":
		switch typed := value.(type) {
		case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
			return true
		case float32:
			return math.Trunc(float64(typed)) == float64(typed)
		case float64:
			return math.Trunc(typed) == typed
		default:
			return false
		}
	case "number":
		switch value.(type) {
		case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, float32, float64:
			return true
		default:
			return false
		}
	default:
		return true
	}
}

func auditEventFromInvocation(session domain.Session, invocation domain.Invocation) AuditEvent {
	return AuditEvent{
		At:            time.Now().UTC(),
		SessionID:     session.ID,
		ToolName:      invocation.ToolName,
		InvocationID:  invocation.ID,
		CorrelationID: invocation.CorrelationID,
		Status:        string(invocation.Status),
		ActorID:       session.Principal.ActorID,
		TenantID:      session.Principal.TenantID,
		Metadata:      session.Metadata,
	}
}

func capabilitySupportedByRuntime(session domain.Session, capability domain.Capability) bool {
	if capability.Scope != domain.ScopeCluster {
		return true
	}
	if session.Runtime.Kind != domain.RuntimeKindKubernetes {
		return false
	}
	if isK8sDeliveryCapability(capability.Name) {
		return envBool("WORKSPACE_ENABLE_K8S_DELIVERY_TOOLS", false)
	}
	return true
}

func unsupportedRuntimeReason(session domain.Session, capability domain.Capability) string {
	if capability.Scope == domain.ScopeCluster {
		if session.Runtime.Kind == "" || session.Runtime.Kind == domain.RuntimeKindLocal {
			return "tool requires kubernetes runtime"
		}
		if isK8sDeliveryCapability(capability.Name) && !envBool("WORKSPACE_ENABLE_K8S_DELIVERY_TOOLS", false) {
			return "k8s delivery tools are disabled by configuration"
		}
		return fmt.Sprintf("tool requires kubernetes runtime (session runtime=%s)", session.Runtime.Kind)
	}
	return "tool is not supported by current runtime"
}

func isK8sDeliveryCapability(name string) bool {
	switch strings.TrimSpace(name) {
	case "k8s.apply_manifest", "k8s.rollout_status", "k8s.restart_deployment":
		return true
	default:
		return false
	}
}

func envBool(name string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(name)))
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	case "":
		return fallback
	default:
		return fallback
	}
}
