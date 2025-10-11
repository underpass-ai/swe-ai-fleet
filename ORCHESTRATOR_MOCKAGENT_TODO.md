# TODO: Reemplazar MockAgent con Agentes Reales

## 🔥 Problema Actual

Actualmente, el Orchestrator Service usa **MockAgent** para testing y desarrollo:
- `CreateCouncil()` crea MockAgents automáticamente
- `RegisterAgent()` registra MockAgents
- Los E2E tests dependen completamente de MockAgent

## ⚠️ Limitaciones de MockAgent

1. **No es production-ready**: MockAgent simula comportamiento, no ejecuta lógica real
2. **Comportamiento predefinido**: Respuestas basadas en `AgentBehavior` enum, no en LLMs reales
3. **Sin inteligencia real**: No aprende, no mejora, no tiene contexto semántico
4. **Dificulta testing de integración real**: Los E2E no validan el flujo completo con LLMs

## 🎯 Solución Propuesta

### Fase 1: Agentes LLM Reales (Corto Plazo)
- Implementar `LLMAgent` que use OpenAI/Anthropic/Local LLMs
- Configurar via environment variables: `AGENT_PROVIDER`, `OPENAI_API_KEY`, etc.
- Mantener MockAgent para unit tests, usar LLMAgent para E2E/staging

### Fase 2: Registry de Agentes (Medio Plazo)
- Crear `AgentRegistry` service independiente
- Permitir registro dinámico de agentes (mock, LLM, human-in-the-loop)
- API REST/gRPC para gestión de agentes
- Persistencia de configuración de agentes

### Fase 3: Agentes Especializados (Largo Plazo)
- Agentes con personalidad/especialización diferenciada
- Fine-tuning por rol (DEV, QA, ARCHITECT, etc.)
- Memory y contexto persistente por agente
- Métricas y evolución de agentes en el tiempo

## 📋 Tareas Concretas

- [ ] Diseñar interfaz `Agent` para soportar múltiples backends
- [ ] Implementar `LLMAgent` con OpenAI/Anthropic
- [ ] Crear factory pattern para instanciar agentes según configuración
- [ ] Modificar `CreateCouncil` para aceptar tipo de agente
- [ ] Crear tests E2E con LLM reales (skip por default, run on-demand)
- [ ] Documentar cómo configurar agentes en producción

## 🚀 Prioridad

**MEDIUM** - El sistema funciona con MockAgent para desarrollo, pero necesitamos
agentes reales para producción. Esto debería abordarse después de:
1. Completar E2E testing con MockAgent
2. Estabilizar APIs core (Context, Orchestrator, Planning)
3. Definir arquitectura de costos para LLM calls

## 📝 Notas

- MockAgent es **perfecto para development/CI** (rápido, determinístico, sin costos)
- Necesitamos agentes reales para **staging/production**
- Considerar rate limiting y costos al implementar LLMAgent
- Explorar modelos locales (Llama, Mistral) para reducir dependencia de APIs externas

