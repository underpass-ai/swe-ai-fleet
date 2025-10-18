# ESLint Configuration - Monitoring Dashboard

## 🎯 Purpose

Configuración restrictiva de ESLint para TypeScript/JavaScript/JSX que impide errores comunes en el desarrollo del dashboard de monitoreo.

## 📋 Reglas Configuradas

### TypeScript Strict Rules
- ❌ **No `any` types**: `@typescript-eslint/no-explicit-any: error`
- ❌ **No unused variables**: `@typescript-eslint/no-unused-vars: error`
- ❌ **No non-null assertions**: `@typescript-eslint/no-non-null-assertion: error`
- ❌ **No floating promises**: `@typescript-eslint/no-floating-promises: error`
- ❌ **No misused promises**: `@typescript-eslint/no-misused-promises: error`
- ❌ **Await thenable**: `@typescript-eslint/await-thenable: error`
- ❌ **No unsafe assignments**: `@typescript-eslint/no-unsafe-assignment: error`
- ❌ **No unsafe member access**: `@typescript-eslint/no-unsafe-member-access: error`
- ❌ **No unsafe calls**: `@typescript-eslint/no-unsafe-call: error`
- ❌ **No unsafe returns**: `@typescript-eslint/no-unsafe-return: error`
- ❌ **Restrict template expressions**: `@typescript-eslint/restrict-template-expressions: error`

### General Code Quality
- ⚠️ **No console logs**: `no-console: warn` (permite `console.warn` y `console.error`)
- ❌ **No debugger**: `no-debugger: error`
- ❌ **No alerts**: `no-alert: error`
- ❌ **No var**: `no-var: error`
- ✅ **Prefer const**: `prefer-const: error`
- ✅ **Prefer arrow functions**: `prefer-arrow-callback: error`
- ❌ **No duplicate imports**: `no-duplicate-imports: error`
- ❌ **No unused expressions**: `no-unused-expressions: error`
- ❌ **No return await**: `no-return-await: error`
- ✅ **Strict equality**: `eqeqeq: ['error', 'always']`

### React Specific
- ✅ **JSX key required**: `react/jsx-key: error`
- ❌ **No duplicate props**: `react/jsx-no-duplicate-props: error`
- ❌ **No undefined components**: `react/jsx-no-undef: error`
- ❌ **No children prop**: `react/no-children-prop: error`
- ❌ **No danger with children**: `react/no-danger-with-children: error`
- ❌ **No direct state mutation**: `react/no-direct-mutation-state: error`
- ❌ **No unknown properties**: `react/no-unknown-property: error`
- ✅ **Self-closing components**: `react/self-closing-comp: error`

### React Hooks
- ❌ **Rules of hooks**: `react-hooks/rules-of-hooks: error`
- ⚠️ **Exhaustive deps**: `react-hooks/exhaustive-deps: warn`

### Accessibility (a11y)
- ❌ **Alt text required**: `jsx-a11y/alt-text: error`
- ⚠️ **Anchor is valid**: `jsx-a11y/anchor-is-valid: warn`
- ⚠️ **Click events with keyboard**: `jsx-a11y/click-events-have-key-events: warn`

## 🚀 Uso

### Linting durante desarrollo
```bash
cd services/monitoring/frontend

# Verificar errores
npm run lint

# Autofix
npm run lint:fix
```

### Build con lint
```bash
# Build normal (incluye lint)
npm run build

# Build sin lint (para Docker)
npm run build:no-lint
```

## 🔧 Workflow de Desarrollo

1. **Desarrollo local**: ESLint se ejecuta en el IDE (VSCode/Cursor)
2. **Pre-commit**: El lint debe pasar antes de commit
3. **CI/CD**: El lint se ejecuta en el pipeline
4. **Docker build**: Usa `build:no-lint` para velocidad

## 📝 Ignorar Archivos

Los siguientes archivos están excluidos en `.eslintignore`:
- `dist/` - Código compilado
- `node_modules/` - Dependencias
- `*.config.js` - Archivos de configuración
- `*.config.ts` - Archivos de configuración TypeScript
- `vite.config.ts` - Configuración de Vite

## 🎓 Ejemplos de Errores Comunes

### ❌ Error: Usar `any`
```typescript
// ❌ MAL
const data: any = await response.json();

// ✅ BIEN
interface ApiResponse {
  connected: boolean;
  error?: string;
}
const data: ApiResponse = await response.json();
```

### ❌ Error: Variables no usadas
```typescript
// ❌ MAL
const [data, setData] = useState(null);
const unused = 123;

// ✅ BIEN
const [data, setData] = useState(null);
const _unused = 123; // Prefijo _ para ignorar
```

### ❌ Error: Promesas flotantes
```typescript
// ❌ MAL
fetchData(); // Promise no manejado

// ✅ BIEN
void fetchData(); // Explícitamente ignorado
// o
fetchData().catch(console.error);
```

### ❌ Error: No usar `==`
```typescript
// ❌ MAL
if (value == null) { }

// ✅ BIEN
if (value === null) { }
```

## 🔍 Integración con IDE

### VSCode/Cursor
Instala la extensión ESLint:
```
dbaeumer.vscode-eslint
```

Configuración recomendada en `.vscode/settings.json`:
```json
{
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact",
    "typescript",
    "typescriptreact"
  ]
}
```

## 📚 Referencias

- [ESLint Rules](https://eslint.org/docs/rules/)
- [TypeScript ESLint](https://typescript-eslint.io/)
- [React ESLint Plugin](https://github.com/jsx-eslint/eslint-plugin-react)
- [JSX a11y Plugin](https://github.com/jsx-eslint/eslint-plugin-jsx-a11y)

