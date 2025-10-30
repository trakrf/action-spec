# Feature: Jinja → Vue 3 SPA Migration (Parity Release)

## Origin
This specification is based on Linear issue D2A-28 with critical scope clarification: **This is a 1:1 migration of existing Jinja templates to Vue 3 SPA, NOT a feature release.** AWS resource pickers and nested YAML editing mentioned in the Linear issue are future enhancements and explicitly OUT OF SCOPE for this migration.

## Outcome
Replace server-side Jinja templates with Vue 3 SPA while maintaining **exact functional parity** with current implementation. Users should experience identical workflows with SPA benefits (faster navigation, no page reloads).

## User Story
As a **DevOps engineer managing infrastructure pods**
I want **the same pod management workflows in a Vue 3 SPA**
So that **I get faster, more responsive UI without learning new processes**

## Context

### Discovery
Current Flask application uses 4 Jinja templates:
- `index.html.j2` - Dashboard listing all pods
- `form.html.j2` - Dual-mode form (create/edit pods)
- `success.html.j2` - Deployment confirmation with PR link
- `error.html.j2` - Error handling with pod suggestions

### Current State
- Server-side rendering (Jinja2)
- Full page reloads on navigation
- HTML forms with POST submissions
- JavaScript for real-time preview only
- Validation: HTML5 pattern + server-side

### Desired State (Parity)
- Client-side rendering (Vue 3 SPA)
- Instant navigation between views
- API calls via Fetch (Flask REST endpoints exist from PR #35)
- Client-side validation matching server rules
- Same visual design and workflows

## Critical Scope Boundaries

### ✅ IN SCOPE (Parity Migration)
- Replicate all 4 existing templates as Vue components
- Maintain exact current workflows
- Use existing Flask API endpoints (no backend changes)
- Client-side validation matching existing server-side rules
- Match current visual design

### ❌ OUT OF SCOPE (Future Enhancements)
- **SubnetPicker component** - Does not exist in current app
- **AMIPicker component** - Does not exist in current app
- **SnapshotPicker component** - Does not exist in current app
- **Recursive nested YAML editor** - Current form has flat fields only
- New validation rules beyond what exists today
- Visual design changes or animations
- Additional form fields or configuration options

## Technical Requirements

### 1. Project Structure
```
src/frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard.vue          # Replicates index.html.j2
│   │   ├── PodForm.vue            # Replicates form.html.j2
│   │   ├── SuccessPage.vue        # Replicates success.html.j2
│   │   └── ErrorPage.vue          # Replicates error.html.j2
│   ├── router/
│   │   └── index.js               # Vue Router matching current routes
│   ├── App.vue
│   └── main.js
├── vite.config.js                 # Proxy /api/* → localhost:5000
└── package.json
```

### 2. Component Specifications

#### Dashboard.vue (index.html.j2 parity)
**Replicate:**
- Fetch pods via `GET /api/pods`
- Group pods by customer
- Display environment badges (dev=green, stg=yellow, prd=red)
- "Refresh" button (clears cache)
- "+ Create New Pod" button
- Pod cards linking to edit form
- Warning if no pods discovered

**Validation:** None (read-only display)

#### PodForm.vue (form.html.j2 parity)
**Replicate:**

**Create Mode (`/pod/new`):**
- Customer dropdown (hardcoded: advworks, northwind, contoso)
- Environment dropdown (hardcoded: dev, stg, prd)
- Instance name text input
- WAF enabled checkbox
- Real-time computed name preview: `{customer}-{env}-{instance_name}`
- Hide breadcrumb navigation

**Edit Mode (`/pod/:customer/:env`):**
- Fetch existing pod via `GET /api/pods/:customer/:env`
- Customer/environment as read-only badges
- Instance name pre-populated and editable
- WAF checkbox pre-populated
- Show breadcrumb navigation
- Real-time preview updates on typing

**Validation (client-side matching server rules):**
- Instance name pattern: `[a-z0-9-]+`
- Instance name length: 1-30 characters
- Cannot start or end with hyphen
- Required fields enforcement

**Submit Behavior:**
- POST to `/api/deploy` with form data
- Disable button and show "Deploying..." spinner
- On success: Navigate to success page with response data
- On error: Navigate to error page with error details

#### SuccessPage.vue (success.html.j2 parity)
**Replicate:**
- Display confirmation message based on mode (create/edit)
- Show workflow inputs sent:
  - Customer
  - Environment
  - Instance Name
  - WAF Enabled status
- Link to GitHub PR (`pr_url`)
- Link to GitHub Actions tab
- "Estimated time: 3-5 minutes" message
- "View Pod" button (navigate to `/pod/:customer/:env`)
- "Back to Home" button

**Validation:** None (display only)

#### ErrorPage.vue (error.html.j2 parity)
**Replicate:**
- Dynamic error icon based on error type:
  - `not_found` → 🔍
  - `validation` → ⚠️
  - `forbidden` → 🔒
  - `api_error` → 🔌
  - `server_error` → 💥
  - default → ❌
- Display `error_title` and `error_message`
- Conditionally show available pods grid (if provided)
- "Back to Home" button

**Validation:** None (display only)

### 3. Routing (Vue Router)
Match existing Flask routes:
- `/` → Dashboard.vue
- `/pod/new` → PodForm.vue (create mode)
- `/pod/:customer/:env` → PodForm.vue (edit mode)
- `/success` → SuccessPage.vue
- `/error` → ErrorPage.vue

### 4. API Integration
Use existing Flask REST endpoints (from PR #35):
- `GET /api/pods` - List all pods
- `GET /api/pods/:customer/:env` - Get specific pod spec
- `POST /api/deploy` - Deploy pod (create or update)
- `POST /api/refresh` - Refresh pod cache

**No backend changes required.**

### 5. Validation Rules (Client-side Implementation)
Replicate existing server-side validation:

```javascript
// Instance name validation (from validate_instance_name)
const instanceNameRules = {
  pattern: /^[a-z0-9-]+$/,
  minLength: 1,
  maxLength: 30,
  noStartEndHyphen: true
}

// Customer/environment validation (from validate_path_component)
const pathComponentRules = {
  pattern: /^[a-zA-Z0-9_-]+$/,
  minLength: 1,
  maxLength: 50,
  noPathTraversal: true  // Reject "..", "/", "\"
}
```

### 6. Styling
- Match current visual design exactly
- Plain CSS (no Tailwind/Bootstrap)
- Reuse existing color scheme:
  - Dev badge: green
  - Staging badge: yellow
  - Production badge: red
- Replicate existing layout and spacing

### 7. Production Build
```bash
npm run build
```
- Configure Flask to serve Vue build from `dist/` in production
- Serve `index.html` for SPA routes (fallback handling)
- Keep `/api/*` routes for backend

## Validation Criteria

### Functional Parity Checklist
- [ ] Dashboard loads and displays all pods grouped by customer
- [ ] Environment badges match current colors (dev=green, stg=yellow, prd=red)
- [ ] Clicking pod card navigates to edit form with pre-populated data
- [ ] "+ Create New Pod" opens blank form
- [ ] Customer and environment dropdowns have same 3 hardcoded options
- [ ] Instance name preview updates in real-time as user types
- [ ] Create mode hides breadcrumb, edit mode shows breadcrumb
- [ ] Form validation catches invalid instance names before submit
- [ ] Submit button shows loading state during deployment
- [ ] Success page displays PR link and workflow inputs
- [ ] Error page shows appropriate error icon and message
- [ ] Error page conditionally shows available pods grid
- [ ] Refresh button clears cache and reloads pods
- [ ] All navigation flows match current Jinja app exactly

### Workflow Validation
**Existing Flow 1: View and Edit Pod**
```
Dashboard → Click pod → Edit form (pre-filled) → Deploy → Success page → View PR
```

**Existing Flow 2: Create New Pod**
```
Dashboard → "+ Create New Pod" → Form (blank) → Deploy → Success page → View PR
```

**Existing Flow 3: Error Handling**
```
Form → Deploy (validation error) → Error page (with suggestions) → Back to dashboard
```

### Regression Prevention
- [ ] No new form fields added
- [ ] No new validation rules beyond existing
- [ ] No AWS resource pickers introduced
- [ ] No nested YAML editor introduced
- [ ] Customer/environment options unchanged (advworks, northwind, contoso / dev, stg, prd)
- [ ] WAF checkbox only (no additional security options)

## Technical Decisions

### Why Vue 3 Composition API?
- Mike already knows Vue (fast execution)
- Lighter than React for form-heavy apps
- `<script setup>` reduces boilerplate

### Why Plain CSS?
- Match existing simple design
- Avoid framework overkill for 4 pages
- Faster iteration

### Why No TypeScript?
- Not mentioned in Linear issue
- Keep it simple for 1-hour estimate
- Can add later if needed

## Implementation Notes

### Phase 1: Scaffold (15 min)
```bash
npm create vue@latest src/frontend
# Select: Vue 3, Vue Router, NO TypeScript, NO Pinia (simple state)
cd src/frontend
npm install
```

### Phase 2: Configure Vite Proxy (5 min)
```javascript
// vite.config.js
export default {
  server: {
    proxy: {
      '/api': 'http://localhost:5000'
    }
  }
}
```

### Phase 3: Build Components (30 min)
- Dashboard.vue (10 min)
- PodForm.vue (15 min - most complex)
- SuccessPage.vue (3 min)
- ErrorPage.vue (2 min)

### Phase 4: Router Setup (5 min)
- Define routes matching Flask routes
- Test navigation

### Phase 5: Integration & Testing (5 min)
- Test full workflows
- Verify API integration
- Check validation behavior

### Phase 6: Production Build (5 min)
```bash
npm run build
# Update Flask app.py to serve dist/ folder
```

## Definition of Done

### Must Have (Parity)
- [ ] All 4 Jinja templates replaced with Vue components
- [ ] All workflows function identically to current app
- [ ] Validation rules match server-side rules exactly
- [ ] Visual design matches current app
- [ ] Production build served by Flask
- [ ] Old Jinja templates removed

### Must NOT Have (Future Features)
- [ ] No SubnetPicker component
- [ ] No AMIPicker component
- [ ] No SnapshotPicker component
- [ ] No recursive YAML editor
- [ ] No new form fields
- [ ] No new validation rules

## Success Metrics
- **User cannot tell the difference** (except SPA feels faster)
- **Zero workflow changes** from current Jinja app
- **Deployment time: 1 hour** (matching Linear estimate)

## Risks & Mitigations

**Risk:** Temptation to add "just one more feature"
**Mitigation:** Strict parity checklist; reject any additions

**Risk:** Over-engineering components
**Mitigation:** Copy existing template logic directly; no abstractions

**Risk:** Missing edge cases in validation
**Mitigation:** Use exact regex patterns from Flask validators

## Next Steps (Post-Migration)
After parity is achieved and deployed:
1. Add SubnetPicker (future PR)
2. Add AMIPicker (future PR)
3. Add SnapshotPicker (future PR)
4. Migrate to nested YAML editor (future PR)

These are explicitly **not** part of this migration spec.

---

## Conversation References
- **User instruction**: "ultrathink to ensure that we are meeting the goal of replicating existing functionality and not anticipating upcoming enhancements. this is a SPA migration not a feature release"
- **Critical finding**: Linear issue D2A-28 includes components (SubnetPicker, AMIPicker, SnapshotPicker) that don't exist in current Jinja templates - these are future enhancements, NOT migration requirements
- **Scope decision**: Focus exclusively on 1:1 replication of 4 existing templates
- **Time estimate**: 1 hour (from Linear issue)
- **Tech stack**: Vue 3 Composition API, Vite, Fetch API, plain CSS (from Linear issue)
