package app

import (
	"context"
	"encoding/json"
	"errors"
	"sort"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
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
	if runErr != nil {
		invocation.Logs = runResult.Logs
		invocation.ExitCode = runResult.ExitCode
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

	artifacts, saveErr := s.artifacts.Save(ctx, invocationID, runResult.Artifacts)
	if saveErr != nil {
		invocation.Logs = runResult.Logs
		invocation.ExitCode = runResult.ExitCode
		invocation = s.finishWithError(invocation, startedAt, &domain.Error{
			Code:      ErrorCodeInternal,
			Message:   saveErr.Error(),
			Retryable: false,
		})
		_ = s.storeInvocation(ctx, invocation)
		s.audit.Record(ctx, auditEventFromInvocation(session, invocation))
		return invocation, internalError(saveErr.Error())
	}

	endedAt := time.Now().UTC()
	invocation.Status = domain.InvocationStatusSucceeded
	invocation.CompletedAt = &endedAt
	invocation.DurationMS = endedAt.Sub(startedAt).Milliseconds()
	invocation.Output = runResult.Output
	invocation.Logs = runResult.Logs
	invocation.Artifacts = artifacts
	invocation.ExitCode = runResult.ExitCode
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
	return invocation, nil
}

func (s *Service) GetInvocationLogs(ctx context.Context, invocationID string) ([]domain.LogLine, *ServiceError) {
	invocation, serviceErr := s.GetInvocation(ctx, invocationID)
	if serviceErr != nil {
		return nil, serviceErr
	}
	return invocation.Logs, nil
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
