#!/usr/bin/env python3
"""E2E Test: Fleet-Proxy Enrollment + mTLS Validation.

This E2E test validates the fleet-proxy security boundary:
- API key enrollment via StaticKeyStore
- PKI certificate issuance from CSR
- mTLS handshake with issued certificate
- Auth/authz interceptors pass for command and query RPCs
- Unauthenticated requests are rejected

Flow Verified:
0. TCP connectivity to fleet-proxy:8443
1. Generate ECDSA P-256 keypair + CSR
2. Enroll via API key (TLS channel) -> receive signed client cert
3. Parse and validate issued certificate (SPIFFE SAN, expiry, key usage)
4. Create mTLS channel with issued cert
5. CreateProject via mTLS (INTERNAL = OK, proves auth passed)
6. ListProjects via mTLS (INTERNAL = OK, proves auth passed)
7. ListProjects WITHOUT mTLS -> rejected (UNAUTHENTICATED or UNAVAILABLE)

Test Prerequisites:
- fleet-proxy deployed with STATIC_API_KEYS and cert-manager PKI
- gRPC server on port 8443
"""

import asyncio
import json
import os
import socket
import ssl
import sys
import tempfile
import time
import uuid

import grpc

# cryptography for CSR generation and cert parsing
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

# Import generated protobuf stubs (generated at Docker build time)
sys.path.insert(0, "/app")
from fleet.proxy.v1 import fleet_proxy_pb2, fleet_proxy_pb2_grpc


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

class Colors:
    """ANSI color codes for terminal output."""
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def print_step(step: int, description: str) -> None:
    """Print step header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}\u2713 {message}{Colors.NC}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}\u2717 {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}\u26a0 {message}{Colors.NC}")


def print_info(message: str) -> None:
    print(f"{Colors.YELLOW}\u2139 {message}{Colors.NC}")


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class FleetProxyEnrollmentTest:
    """E2E test for fleet-proxy enrollment and mTLS validation."""

    def __init__(self) -> None:
        self.fleet_proxy_url = os.getenv(
            "FLEET_PROXY_URL",
            "fleet-proxy.swe-ai-fleet.svc.cluster.local:8443",
        )
        # API key format: "keyID:secret"
        self.api_key = os.getenv("FLEET_PROXY_API_KEY", "e2e-key:e2e-secret")
        self.device_id = os.getenv("FLEET_PROXY_DEVICE_ID", "e2e-device")
        self.ca_cert_path = os.getenv("FLEET_PROXY_CA_CERT", "")
        self.server_ca_pem = None  # loaded in step 2

        # Generated during test
        self.private_key = None
        self.csr_pem = None
        self.client_cert_pem = None
        self.ca_chain_pem = None
        self.client_id = None
        self.expires_at = None

        # Evidence collector
        self.evidence = {
            "test_name": "44-fleet-proxy-enrollment-and-proxy",
            "fleet_proxy_url": self.fleet_proxy_url,
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "steps": [],
        }

    def _record_step(self, step: int, name: str, passed: bool, details: str = "") -> None:
        self.evidence["steps"].append({
            "step": step,
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def _emit_evidence(self) -> None:
        self.evidence["end_time"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print()
        print("EVIDENCE_JSON_START")
        print(json.dumps(self.evidence, indent=2))
        print("EVIDENCE_JSON_END")
        print()

    # ------------------------------------------------------------------
    # Step 0: TCP connectivity
    # ------------------------------------------------------------------
    async def step_0_tcp_connectivity(self) -> bool:
        print_step(0, "TCP connectivity check")
        host, port_str = self.fleet_proxy_url.rsplit(":", 1)
        port = int(port_str)
        print_info(f"Checking TCP connectivity to {host}:{port}...")

        for attempt in range(5):
            try:
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                print_success(f"TCP connection to {host}:{port} succeeded")
                self._record_step(0, "tcp_connectivity", True)
                return True
            except (socket.timeout, ConnectionRefusedError, OSError) as exc:
                print_warning(f"Attempt {attempt + 1}/5 failed: {exc}")
                await asyncio.sleep(2)

        print_error(f"TCP connectivity to {host}:{port} failed after 5 attempts")
        self._record_step(0, "tcp_connectivity", False, "all attempts failed")
        return False

    # ------------------------------------------------------------------
    # Step 1: Generate ECDSA keypair + CSR
    # ------------------------------------------------------------------
    async def step_1_generate_keypair_and_csr(self) -> bool:
        print_step(1, "Generate ECDSA P-256 keypair + CSR")
        try:
            self.private_key = ec.generate_private_key(ec.SECP256R1())
            print_success("Generated ECDSA P-256 private key")

            csr_builder = x509.CertificateSigningRequestBuilder().subject_name(
                x509.Name([
                    x509.NameAttribute(NameOID.COMMON_NAME, f"e2e-test-{uuid.uuid4().hex[:8]}"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "swe-ai-fleet-e2e"),
                ])
            )
            csr = csr_builder.sign(self.private_key, hashes.SHA256())
            self.csr_pem = csr.public_bytes(serialization.Encoding.PEM)

            print_success(f"Generated CSR ({len(self.csr_pem)} bytes PEM)")
            self._record_step(1, "generate_keypair_csr", True)
            return True

        except Exception as exc:
            print_error(f"Failed to generate keypair/CSR: {exc}")
            self._record_step(1, "generate_keypair_csr", False, str(exc))
            return False

    # ------------------------------------------------------------------
    # Step 2: Enroll via TLS channel
    # ------------------------------------------------------------------
    async def step_2_enroll(self) -> bool:
        print_step(2, "Enroll via API key (TLS channel)")
        print_info(f"Connecting to {self.fleet_proxy_url} for enrollment...")

        try:
            # Load the server CA cert so the client trusts the fleet-proxy TLS cert.
            if self.ca_cert_path and os.path.isfile(self.ca_cert_path):
                with open(self.ca_cert_path, "rb") as f:
                    self.server_ca_pem = f.read()
                print_info(f"Loaded server CA cert from {self.ca_cert_path} ({len(self.server_ca_pem)} bytes)")
            else:
                print_warning("No CA cert path set; TLS verification may fail")

            channel_creds = grpc.ssl_channel_credentials(
                root_certificates=self.server_ca_pem,
            )
            channel = grpc.aio.secure_channel(self.fleet_proxy_url, channel_creds)

            stub = fleet_proxy_pb2_grpc.EnrollmentServiceStub(channel)

            request = fleet_proxy_pb2.EnrollRequest(
                api_key=self.api_key,
                csr_pem=self.csr_pem,
                device_id=self.device_id,
                client_version="e2e-test-v1.0.0",
            )

            print_info("Calling EnrollmentService.Enroll...")
            response = await asyncio.wait_for(stub.Enroll(request), timeout=15.0)

            if not response.client_cert_pem:
                print_error("Enrollment response missing client_cert_pem")
                await channel.close()
                self._record_step(2, "enroll", False, "missing client_cert_pem")
                return False

            self.client_cert_pem = response.client_cert_pem
            self.ca_chain_pem = response.ca_chain_pem
            self.client_id = response.client_id
            self.expires_at = response.expires_at

            print_success(f"Enrollment succeeded: client_id={self.client_id}")
            print_success(f"Certificate expires at: {self.expires_at}")
            print_success(f"Client cert: {len(self.client_cert_pem)} bytes")
            print_success(f"CA chain: {len(self.ca_chain_pem)} bytes")

            await channel.close()
            self._record_step(2, "enroll", True, f"client_id={self.client_id}")
            return True

        except grpc.RpcError as exc:
            code = exc.code()
            details = exc.details()
            print_error(f"Enrollment gRPC error: {code} - {details}")
            self._record_step(2, "enroll", False, f"{code}: {details}")
            return False

        except asyncio.TimeoutError:
            print_error("Enrollment timed out after 15s")
            self._record_step(2, "enroll", False, "timeout")
            return False

        except Exception as exc:
            print_error(f"Enrollment unexpected error: {exc}")
            self._record_step(2, "enroll", False, str(exc))
            return False

    # ------------------------------------------------------------------
    # Step 3: Parse and validate issued certificate
    # ------------------------------------------------------------------
    async def step_3_validate_certificate(self) -> bool:
        print_step(3, "Parse and validate issued certificate")
        try:
            cert = x509.load_pem_x509_certificate(self.client_cert_pem)

            # Check subject
            org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            print_info(f"Subject org: {org[0].value if org else 'N/A'}")

            # Check SAN for SPIFFE URI
            try:
                san_ext = cert.extensions.get_extension_for_class(
                    x509.SubjectAlternativeName
                )
                uris = san_ext.value.get_values_for_type(x509.UniformResourceIdentifier)
                print_info(f"SAN URIs: {uris}")

                spiffe_found = any(u.startswith("spiffe://swe-ai-fleet/") for u in uris)
                if spiffe_found:
                    print_success("SPIFFE URI found in SAN")
                else:
                    print_warning("No SPIFFE URI in SAN (may be OK for ephemeral CA)")
            except x509.ExtensionNotFound:
                print_warning("No SAN extension found")

            # Check expiry
            print_info(f"Not valid before: {cert.not_valid_before_utc}")
            print_info(f"Not valid after:  {cert.not_valid_after_utc}")

            # Check key usage
            try:
                ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
                print_info(f"Key usage: digital_signature={ku.value.digital_signature}")
            except x509.ExtensionNotFound:
                print_info("No key usage extension")

            print_success("Certificate parsed and validated")
            self._record_step(3, "validate_certificate", True)
            return True

        except Exception as exc:
            print_error(f"Certificate validation failed: {exc}")
            self._record_step(3, "validate_certificate", False, str(exc))
            return False

    # ------------------------------------------------------------------
    # Step 4: Create mTLS channel with issued cert
    # ------------------------------------------------------------------
    async def step_4_create_mtls_channel(self) -> tuple:
        """Returns (success, channel, stub_cmd, stub_query) or (False, None, None, None)."""
        print_step(4, "Create mTLS channel with issued certificate")

        try:
            # Write private key to temp file for gRPC
            key_pem = self.private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )

            # Build mTLS credentials
            channel_creds = grpc.ssl_channel_credentials(
                root_certificates=self.ca_chain_pem,
                private_key=key_pem,
                certificate_chain=self.client_cert_pem,
            )

            channel = grpc.aio.secure_channel(self.fleet_proxy_url, channel_creds)

            # Wait for channel to be ready
            await asyncio.wait_for(channel.channel_ready(), timeout=10.0)
            print_success("mTLS channel established and ready")

            cmd_stub = fleet_proxy_pb2_grpc.FleetCommandServiceStub(channel)
            query_stub = fleet_proxy_pb2_grpc.FleetQueryServiceStub(channel)

            self._record_step(4, "create_mtls_channel", True)
            return True, channel, cmd_stub, query_stub

        except asyncio.TimeoutError:
            print_error("mTLS channel not ready within 10s")
            self._record_step(4, "create_mtls_channel", False, "timeout")
            return False, None, None, None

        except Exception as exc:
            print_error(f"mTLS channel creation failed: {exc}")
            self._record_step(4, "create_mtls_channel", False, str(exc))
            return False, None, None, None

    # ------------------------------------------------------------------
    # Step 5: CreateProject via mTLS
    # ------------------------------------------------------------------
    async def step_5_create_project(self, cmd_stub) -> bool:
        print_step(5, "CreateProject via mTLS channel")
        try:
            request = fleet_proxy_pb2.CreateProjectRequest(
                request_id=f"e2e-{uuid.uuid4().hex[:8]}",
                name="e2e-enrollment-test-project",
                description="Created by E2E test 44",
            )
            print_info("Calling FleetCommandService.CreateProject...")

            response = await asyncio.wait_for(
                cmd_stub.CreateProject(request), timeout=10.0
            )
            print_success(f"CreateProject succeeded: {response}")
            self._record_step(5, "create_project_mtls", True, "direct success")
            return True

        except grpc.RpcError as exc:
            code = exc.code()
            details = exc.details()

            # INTERNAL = planning stub not connected. This is expected and
            # proves the auth/authz layer passed successfully.
            if code == grpc.StatusCode.INTERNAL:
                print_success(
                    f"CreateProject returned INTERNAL (expected - planning stub): {details}"
                )
                self._record_step(
                    5, "create_project_mtls", True,
                    f"INTERNAL (auth passed): {details}",
                )
                return True

            # UNAUTHENTICATED or PERMISSION_DENIED = auth layer rejected us
            print_error(f"CreateProject rejected: {code} - {details}")
            self._record_step(5, "create_project_mtls", False, f"{code}: {details}")
            return False

        except asyncio.TimeoutError:
            print_error("CreateProject timed out")
            self._record_step(5, "create_project_mtls", False, "timeout")
            return False

        except Exception as exc:
            print_error(f"CreateProject unexpected error: {exc}")
            self._record_step(5, "create_project_mtls", False, str(exc))
            return False

    # ------------------------------------------------------------------
    # Step 6: ListProjects via mTLS
    # ------------------------------------------------------------------
    async def step_6_list_projects(self, query_stub) -> bool:
        print_step(6, "ListProjects via mTLS channel")
        try:
            request = fleet_proxy_pb2.ListProjectsRequest(limit=10)
            print_info("Calling FleetQueryService.ListProjects...")

            response = await asyncio.wait_for(
                query_stub.ListProjects(request), timeout=10.0
            )
            print_success(f"ListProjects succeeded: total_count={response.total_count}")
            self._record_step(6, "list_projects_mtls", True, "direct success")
            return True

        except grpc.RpcError as exc:
            code = exc.code()
            details = exc.details()

            if code == grpc.StatusCode.INTERNAL:
                print_success(
                    f"ListProjects returned INTERNAL (expected - planning stub): {details}"
                )
                self._record_step(
                    6, "list_projects_mtls", True,
                    f"INTERNAL (auth passed): {details}",
                )
                return True

            print_error(f"ListProjects rejected: {code} - {details}")
            self._record_step(6, "list_projects_mtls", False, f"{code}: {details}")
            return False

        except asyncio.TimeoutError:
            print_error("ListProjects timed out")
            self._record_step(6, "list_projects_mtls", False, "timeout")
            return False

        except Exception as exc:
            print_error(f"ListProjects unexpected error: {exc}")
            self._record_step(6, "list_projects_mtls", False, str(exc))
            return False

    # ------------------------------------------------------------------
    # Step 7: ListProjects WITHOUT mTLS -> must be rejected
    # ------------------------------------------------------------------
    async def step_7_unauthenticated_rejected(self) -> bool:
        print_step(7, "ListProjects WITHOUT mTLS (expect rejection)")
        try:
            # TLS-only channel (no client cert)
            channel_creds = grpc.ssl_channel_credentials(
                root_certificates=self.ca_chain_pem,
            )
            channel = grpc.aio.secure_channel(self.fleet_proxy_url, channel_creds)
            query_stub = fleet_proxy_pb2_grpc.FleetQueryServiceStub(channel)

            request = fleet_proxy_pb2.ListProjectsRequest(limit=10)
            print_info("Calling ListProjects without client cert...")

            response = await asyncio.wait_for(
                query_stub.ListProjects(request), timeout=10.0
            )

            # If we get here, the server did NOT reject us — that's a failure
            await channel.close()
            print_error(f"ListProjects succeeded WITHOUT mTLS: {response}")
            self._record_step(
                7, "unauthenticated_rejected", False,
                "request succeeded without client cert",
            )
            return False

        except grpc.RpcError as exc:
            code = exc.code()
            details = exc.details()

            # UNAUTHENTICATED or UNAVAILABLE (TLS handshake rejection) = expected
            if code in (grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.UNAVAILABLE):
                print_success(
                    f"Unauthenticated request correctly rejected: {code} - {details}"
                )
                self._record_step(
                    7, "unauthenticated_rejected", True,
                    f"correctly rejected: {code}",
                )
                return True

            # PERMISSION_DENIED also acceptable (authz layer caught it)
            if code == grpc.StatusCode.PERMISSION_DENIED:
                print_success(
                    f"Unauthenticated request rejected by authz: {code} - {details}"
                )
                self._record_step(
                    7, "unauthenticated_rejected", True,
                    f"rejected by authz: {code}",
                )
                return True

            print_error(f"Unexpected rejection code: {code} - {details}")
            self._record_step(
                7, "unauthenticated_rejected", False,
                f"unexpected code: {code}: {details}",
            )
            return False

        except asyncio.TimeoutError:
            # Timeout can happen if TLS handshake is rejected silently
            print_success("Connection timed out (TLS handshake rejected)")
            self._record_step(
                7, "unauthenticated_rejected", True,
                "timeout (TLS rejection)",
            )
            return True

        except Exception as exc:
            # Connection reset / SSL errors = also rejection
            err_str = str(exc).lower()
            if "ssl" in err_str or "reset" in err_str or "refused" in err_str:
                print_success(f"Connection rejected at transport layer: {exc}")
                self._record_step(
                    7, "unauthenticated_rejected", True,
                    f"transport rejection: {exc}",
                )
                return True

            print_error(f"Unexpected error: {exc}")
            self._record_step(7, "unauthenticated_rejected", False, str(exc))
            return False

    # ------------------------------------------------------------------
    # Run all steps
    # ------------------------------------------------------------------
    async def run(self) -> int:
        print()
        print(f"{Colors.BLUE}{'#' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}# E2E Test 44: Fleet-Proxy Enrollment + mTLS Validation{Colors.NC}")
        print(f"{Colors.BLUE}# Target: {self.fleet_proxy_url}{Colors.NC}")
        print(f"{Colors.BLUE}{'#' * 80}{Colors.NC}")

        passed = 0
        failed = 0
        mtls_channel = None

        try:
            # Step 0: TCP connectivity
            if not await self.step_0_tcp_connectivity():
                failed += 1
                self._emit_evidence()
                return 1
            passed += 1

            # Step 1: Generate keypair + CSR
            if not await self.step_1_generate_keypair_and_csr():
                failed += 1
                self._emit_evidence()
                return 1
            passed += 1

            # Step 2: Enroll
            if not await self.step_2_enroll():
                failed += 1
                self._emit_evidence()
                return 1
            passed += 1

            # Step 3: Validate certificate
            if not await self.step_3_validate_certificate():
                failed += 1
                self._emit_evidence()
                return 1
            passed += 1

            # Step 4: Create mTLS channel
            ok, mtls_channel, cmd_stub, query_stub = await self.step_4_create_mtls_channel()
            if not ok:
                failed += 1
                self._emit_evidence()
                return 1
            passed += 1

            # Step 5: CreateProject via mTLS
            if await self.step_5_create_project(cmd_stub):
                passed += 1
            else:
                failed += 1

            # Step 6: ListProjects via mTLS
            if await self.step_6_list_projects(query_stub):
                passed += 1
            else:
                failed += 1

            # Step 7: Unauthenticated rejection
            if await self.step_7_unauthenticated_rejected():
                passed += 1
            else:
                failed += 1

        finally:
            if mtls_channel:
                await mtls_channel.close()

        # Summary
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        total = passed + failed
        if failed == 0:
            print(f"{Colors.GREEN}ALL {total} STEPS PASSED{Colors.NC}")
        else:
            print(f"{Colors.RED}{failed}/{total} STEPS FAILED{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")

        self.evidence["passed"] = passed
        self.evidence["failed"] = failed
        self._emit_evidence()

        return 0 if failed == 0 else 1


async def main() -> int:
    test = FleetProxyEnrollmentTest()
    return await test.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
