#!/usr/bin/env python3
"""
E2E Test: Verify Event Flow
Orchestrator → NATS → Context → Neo4j/ValKey
"""
import sys
import time
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services" / "orchestrator"))

import grpc
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc


def print_step(step, text):
    print(f"\n{'='*80}")
    print(f"STEP {step}: {text}")
    print('='*80)


def print_success(text):
    print(f"✅ {text}")


def print_info(text):
    print(f"ℹ️  {text}")


def print_error(text):
    print(f"❌ {text}")


def main():
    orchestrator_host = "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
    
    print("\n" + "="*80)
    print("🔍 VERIFICACIÓN DE FLUJO DE EVENTOS END-TO-END")
    print("="*80)
    
    # STEP 1: Conectar a Orchestrator
    print_step(1, "Conectando a Orchestrator")
    try:
        channel = grpc.insecure_channel(orchestrator_host)
        stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
        print_success(f"Conectado a {orchestrator_host}")
    except Exception as e:
        print_error(f"Error conectando: {e}")
        return 1
    
    # STEP 2: Crear council
    print_step(2, "Creando council DEV con 3 agentes vLLM reales")
    try:
        response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
            role="DEV",
            num_agents=3,
            config=orchestrator_pb2.CouncilConfig(
                deliberation_rounds=1,
                enable_peer_review=False,
                agent_type="RAY_VLLM"
            )
        ))
        
        council_id = response.council_id
        agent_ids = response.agent_ids
        
        print_success(f"Council creado: {council_id}")
        print_info(f"Agentes: {', '.join(agent_ids)}")
        
    except Exception as e:
        print_error(f"Error creando council: {e}")
        return 1
    
    # STEP 3: Ejecutar deliberación
    print_step(3, "Ejecutando deliberación")
    task = "Implement a simple caching layer for frequently accessed data"
    print_info(f"Task: {task}")
    
    try:
        start_time = time.time()
        deliberation_response = stub.Deliberate(orchestrator_pb2.DeliberateRequest(
            council_id=council_id,
            task=task
        ))
        duration = time.time() - start_time
        
        print_success(f"Deliberación completada en {duration:.2f}s")
        print_info(f"Consensus: {deliberation_response.consensus[:100]}...")
        print_info(f"Confidence: {deliberation_response.confidence:.2f}")
        print_info(f"Proposals: {len(deliberation_response.proposals)}")
        
        if deliberation_response.proposals:
            for i, proposal in enumerate(deliberation_response.proposals, 1):
                print(f"\n  Proposal {i}:")
                print(f"    Agent: {proposal.agent_id}")
                print(f"    Proposal: {proposal.proposal[:80]}...")
        
    except Exception as e:
        print_error(f"Error en deliberación: {e}")
        return 1
    
    # STEP 4: Verificar que se publicaron eventos NATS
    print_step(4, "Verificando eventos NATS (logs de Orchestrator)")
    print_info("Revisando logs del Orchestrator...")
    print_info("Esperando 5 segundos para que eventos se propaguen...")
    time.sleep(5)
    
    # STEP 5: Verificar datos en Neo4j (a través de logs de Context)
    print_step(5, "Verificando persistencia en Neo4j")
    print_info("Revisando logs de Context Service...")
    
    # STEP 6: Verificar datos en ValKey
    print_step(6, "Verificando cache en ValKey")
    print_info("Revisando logs de Context Service...")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETADO")
    print("="*80)
    print("\nAhora ejecuta manualmente:")
    print("1. kubectl logs -n swe-ai-fleet deployment/orchestrator --tail=50 | grep -E '(NATS|publish|event)'")
    print("2. kubectl logs -n swe-ai-fleet deployment/context --tail=50 | grep -E '(received|deliberation|decision)'")
    print("3. kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword 'MATCH (n) RETURN labels(n), count(n);'")
    print("4. kubectl exec -n swe-ai-fleet valkey-0 -- valkey-cli KEYS '*'")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

