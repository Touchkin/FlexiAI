# Phase 1.11: Additional Unit Tests - Implementation Plan

## Current Coverage Status
- Overall: 98% (1169 statements, 26 missing)
- Most modules: 100% coverage ✅
- Need to improve:
  - circuit_breaker/breaker.py: 96% (missing lines 194-198, 212, 228)
  - circuit_breaker/state.py: 98% (missing line 28)
  - client.py: 94% (missing lines 83, 122, 246-259)
  - config.py: 93% (missing lines 159-160, 252-253, 314, 319-320, 361)
  - models.py: 98% (missing lines 156, 250, 396)
  - providers/base.py: 98% (missing line 235)
  - utils/logger.py: 98% (missing lines 68, 158)

## Tests to Add

### 1. Circuit Breaker Edge Cases (test_circuit_breaker.py)
- [ ] Test HALF_OPEN state with failure (reopens circuit) - Line 194-198
- [ ] Test unexpected exceptions not in expected list - Line 212
- [ ] Test success in HALF_OPEN state with max_failures threshold - Line 228

### 2. Config Edge Cases (test_config.py)
- [ ] Test from_yaml with invalid YAML - Lines 159-160
- [ ] Test from_json with invalid JSON - Lines 252-253
- [ ] Test from_env with missing/invalid env vars - Lines 314, 319-320, 361

### 3. Client Edge Cases (test_client.py)
- [ ] Test _create_provider with unsupported provider - Line 122
- [ ] Test chat_completion with empty provider list - Line 83
- [ ] Test error message formatting - Lines 246-259

### 4. Models Edge Cases (test_models.py)
- [ ] Test UnifiedRequest with tools - Line 156
- [ ] Test ProviderConfig with invalid priority - Line 250
- [ ] Test UnifiedResponse with missing optional fields - Line 396

### 5. Integration-Like Unit Tests
- [ ] Test complete failover scenario with multiple providers
- [ ] Test circuit breaker integration with real failure patterns
- [ ] Test config loading from all sources (YAML, JSON, dict, env)
- [ ] Test model validation edge cases

### 6. Additional Validation Tests
- [ ] Test APIKeyValidator with various invalid formats
- [ ] Test ModelValidator with unsupported models
- [ ] Test RequestValidator with invalid parameters

## Goal
- Achieve 99%+ coverage
- Cover all edge cases and error paths
- Ensure robust error handling
- Document any intentionally uncovered code

## Estimated Tests to Add
- Circuit Breaker: +5 tests
- Config: +8 tests
- Client: +3 tests
- Models: +5 tests
- Integration scenarios: +5 tests
- **Total: ~26 new tests** (bringing total from 365 to ~391)
