# Phase 1 Provider Contract - Rollback and Validation Guide

## Quick Validation

### Test New Contract Modules
Run the validation script:
```bash
PYTHONPATH=/home/runner/work/sahasrahbot/sahasrahbot python3 /tmp/test_provider_contract.py
```

Expected output: All three validation tests should pass.

### Verify No Breaking Changes
The Phase 1 implementation is **purely additive**:
- New modules added under `alttprbot/alttprgen/`:
  - `provider_exceptions.py` - Exception taxonomy
  - `provider_response.py` - Response object
  - `provider_wrapper.py` - Execution wrapper
  - `provider_adapters.py` - Provider adapters (with legacy compatibility)
- **No existing code was modified**
- All legacy imports continue to work unchanged

## Rollback Procedure

If issues are discovered after merge, rollback is straightforward:

### Option 1: Git Revert (Recommended)
```bash
git revert <commit-hash>
git push origin main
```

This removes the four new files without affecting any existing functionality.

### Option 2: Manual Removal
```bash
cd /home/runner/work/sahasrahbot/sahasrahbot
rm alttprbot/alttprgen/provider_exceptions.py
rm alttprbot/alttprgen/provider_response.py
rm alttprbot/alttprgen/provider_wrapper.py
rm alttprbot/alttprgen/provider_adapters.py
git add -u
git commit -m "Rollback Phase 1 provider contract implementation"
git push origin main
```

## Verification After Rollback

1. Verify application starts successfully:
   ```bash
   python3 sahasrahbot.py
   ```

2. Test existing seed generation workflows:
   - Discord seed generation commands
   - RaceTime seed generation
   - API seed endpoints

All should continue working as before since Phase 1 did not modify existing code paths.

## Phase 2 Migration Strategy

When ready to proceed with Phase 2:

1. **Gradual Provider Migration**: Migrate one provider at a time to use the new contract
2. **Canary Testing**: Test migrated providers in dev/staging before production
3. **Feature Flags**: Consider adding feature flags to toggle between legacy and contract paths
4. **Monitoring**: Add metrics to compare legacy vs. contract execution paths

## Known Limitations (Phase 1)

- SMDashProvider adapter is implemented but **not yet used** by production code
- Legacy compatibility wrappers maintain exact original behavior
- No audit integration yet (Phase 3)
- Surface cleanup deferred to Phase 4

## Support

For issues or questions about the provider contract implementation:
- Review design doc: `docs/design/seed_provider_reliability_contract.md`
- Review implementation plan: `docs/plans/seed_provider_reliability_implementation_plan.md`
- Check context: `docs/context/system_patterns.md` (Provider Reliability Contract section)
