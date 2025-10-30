# Feature: Archive Overengineered Implementation

## Origin
This specification emerged from recognizing that the initial Lambda/API Gateway/React implementation was significantly overengineered for the actual requirements of the spec editor. Rather than delete this work, we're preserving it as a learning artifact that demonstrates engineering judgment.

**Linear Issue**: D2A-25
**Branch**: `refactor/archive-overengineered`

## Outcome
The overengineered implementation will be moved to `/overengineered/` with clear documentation explaining why it was the wrong approach, while remaining accessible as proof of technical capability and mature decision-making.

## User Story
As a **portfolio reviewer** (recruiter, potential employer, future team member)
I want **to see evidence that the engineer recognizes when they've overcomplicated a solution**
So that **I can trust their judgment on architecture decisions**

## Context

**Discovery**: Built a full Lambda/API Gateway/React stack for what turned out to be a simple spec editor need. The `/demo` POC with Flask and Jinja proved the concept could be solved with far less complexity.

**Current Problem**:
- Overengineered code exists in `/backend/lambda/`, `/frontend/`, `/infrastructure/`
- It demonstrates technical capability but poor judgment if left as the main implementation
- Simply deleting it loses the opportunity to show learning and course-correction

**Desired State**:
- Overengineered code preserved in `/overengineered/` with clear warnings
- Explanatory README that honestly describes what went wrong
- Git history shows intentional archival, not abandonment
- Portfolio narrative: "I can build complex systems AND know when not to"

## Technical Requirements

### File Moves (Structure Preservation)
- [ ] Create `/overengineered/` root directory
- [ ] Move `/backend/lambda/` → `/overengineered/backend/lambda/`
- [ ] Move `/frontend/` → `/overengineered/frontend/`
- [ ] Move `/infrastructure/` → `/overengineered/infrastructure/`
- [ ] Move `/PRD.md` → `/overengineered/PRD.md`

### Documentation (Critical Deliverable)
- [ ] Create `/overengineered/README.md` with:
  - **Warning**: "Don't use this - use /src instead"
  - **What's wrong**: Scale assumptions, cost implications, unnecessary complexity
  - **Why it's kept**: Portfolio value, demonstrates learning and judgment
  - **Context**: When it was built, what we learned, why we pivoted
  - Tone: Honest, self-aware, educational (not defensive)

### Maintenance
- [ ] Update any internal cross-references (if any exist in docs/configs)
- [ ] Ensure archived code remains readable (no broken imports that would confuse reviewers)
- [ ] Verify `.gitignore` doesn't exclude the archived directory

### Quality Gates
- [ ] Can a reviewer understand the mistake without asking questions?
- [ ] Is it absolutely clear this code should NOT be used?
- [ ] Does the README enhance the portfolio narrative?
- [ ] Are the original files completely removed from their old locations?

## README Template (Draft)

```markdown
# Overengineered Implementation (Archived)

⚠️ **DO NOT USE THIS CODE**
This is an archived implementation kept for portfolio and learning purposes.
**Use `/src` instead** for the actual working implementation.

## What's Here

A fully-featured implementation using:
- AWS Lambda for backend logic
- API Gateway for REST endpoints
- React for the frontend UI
- CloudFormation/Terraform for infrastructure

## What Went Wrong

**Scale Assumptions**: Designed for 100K+ requests/day when actual need was <100/day
**Cost**: ~$50-100/month AWS costs vs $5/month for simpler hosting
**Complexity**:
- 3 deployment pipelines vs 1
- Separate frontend/backend repos vs monorepo
- Infrastructure as code vs simple container
- 2000+ lines of code vs 300

**Root Cause**: Started with assumptions about scale before validating actual requirements.

## Why It's Kept

This demonstrates:
1. **Technical Capability**: I can build production-grade serverless architectures
2. **Engineering Judgment**: I can recognize when I've overcomplicated things
3. **Course Correction**: I'm willing to pivot when the evidence says to
4. **Maturity**: Keeping this as a cautionary tale rather than hiding the mistake

## What We Learned

- Start with the simplest thing that could work
- Validate scale requirements before architecting for them
- POCs should disprove assumptions, not confirm them
- Sometimes Flask + Jinja beats Lambda + React

## Timeline

- **Week 1-2**: Built this implementation based on initial PRD
- **Week 3**: Built `/demo` as a "quick POC"
- **Week 3**: Realized the POC solved the problem completely
- **Week 4**: Made the decision to archive this and promote `/demo`

---

*If you're a recruiter/interviewer reading this: Yes, I overengineered this. The difference is I caught it, learned from it, and pivoted. That's the skill that matters.*
```

## Validation Criteria

**Success Metrics**:
- [ ] A portfolio reviewer can read `/overengineered/README.md` and understand the full story in 2 minutes
- [ ] The explanation is honest without being self-deprecating
- [ ] It's immediately obvious NOT to use this code
- [ ] The original directories are completely empty (moved, not copied)
- [ ] Git commit message clearly states "archive overengineered implementation"

**Test Cases**:
- [ ] Show `/overengineered/README.md` to someone unfamiliar with the project - can they explain back what happened?
- [ ] Check that no other docs reference the old paths
- [ ] Verify the directory structure is preserved (someone could still read the code)

**Edge Cases**:
- [ ] If there are hardcoded paths in the archived code, add a note in README that it won't run as-is
- [ ] If there are secrets/credentials in the archived code, remove them before archiving
- [ ] If git history references the old paths, that's fine - the moves will be tracked

## Implementation Notes

**Order matters**:
1. Create `/overengineered/` structure first
2. Move files (git mv for proper history tracking)
3. Write README last (after seeing what's actually there)
4. Test that original locations are empty
5. Commit with descriptive message

**Git approach**:
```bash
# Use git mv to preserve history
git mv backend/lambda overengineered/backend/lambda
git mv frontend overengineered/frontend
# etc.
```

**Time estimate**: 15 minutes
- 5 min: File moves
- 8 min: README writing
- 2 min: Verification

## Conversation References

**Key insight**: "Shows engineering judgment: 'I can build complex systems AND know when not to'" (from D2A-25)

**Decision**: Keep D2A-25 separate from D2A-26 for git history clarity - two PRs tell a better story than one

**Portfolio value**: This isn't just code cleanup - it's a narrative piece that demonstrates maturity and learning

## Anti-patterns to Avoid

- ❌ Don't just move files without the explanatory README (the README is the point)
- ❌ Don't be defensive or apologetic in the README (be matter-of-fact)
- ❌ Don't make the README too long (2-minute read max)
- ❌ Don't copy files (move them - we want clean separation)
- ❌ Don't delete files (defeats the portfolio purpose)

## Related Work

- **D2A-26**: Promote `/demo` to `/src` (should be done after this)
- **Portfolio narrative**: This PR sets up the "before" state; D2A-26 provides the "after"
