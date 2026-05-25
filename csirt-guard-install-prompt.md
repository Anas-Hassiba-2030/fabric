# Install: Cisco IT/CSIRT Hard Guardrails for Claude Code

**Paste this entire document into a fresh Claude Code session as your first
prompt.** Claude will explain what it's about to do, ask you to confirm, then
install a `PreToolUse` hook plus matching `CLAUDE.md` rules that hard-block:

1. Installation of any Claude Code plugin from a marketplace other than
   `claude-plugins-official`.
2. Installation of any skill or file that lands under an unapproved
   AI-agent platform directory: `.openclaw/`, `.hermes/`, `.kiro/`,
   `.factory/`, `.slate/`, `.gbrain/`, `.opencode/`, `.agents/`.

`.cursor/` is intentionally **permitted** because Cursor IDE is an approved
editor. Adjust the platform list before running if your team's allowlist
differs.

The hook fires before every `Write`, `Edit`, `MultiEdit`, and `Bash` tool
call. Blocked calls exit with code 2 and surface a `BLOCKED by CSIRT policy`
message back to Claude. This is harness-level enforcement — Claude cannot
talk its way around the hook.

---

## Instructions for the receiving Claude session

You are about to install IT/CSIRT enforcement on this user's machine.
Follow these steps **in order**. Do not skip the confirmation step.

### Step 1 — Show the user what you will do, and ask for confirmation

Paste the following summary to the user and stop until they confirm:

> I'm about to install a Cisco IT/CSIRT enforcement layer on this Mac:
>
> 1. Write a Node hook script to `~/.claude/hooks/csirt-guard.js`
> 2. Register it as a `PreToolUse` hook in `~/.claude/settings.json`
>    (merging with any existing hooks, not clobbering)
> 3. Append two `⛔ HARD RULE` sections to `~/.claude/CLAUDE.md`
>    (creating the file if it doesn't exist)
> 4. Back up both files first to `*.pre-csirt-guard-<timestamp>`
> 5. Run a battery of unit tests to verify the hook works
>
> After install, the hook will block any tool call that tries to install a
> non-official Claude Code plugin or any skill targeting `.openclaw/`,
> `.hermes/`, `.kiro/`, `.factory/`, `.slate/`, `.gbrain/`, `.opencode/`,
> or `.agents/` directories. Cursor IDE (`.cursor/`) is permitted.
>
> Confirm to proceed?

If the user says no, stop. If yes, continue.

### Step 2 — Detect environment

Run these to determine the right paths for this machine:

```bash
echo "HOME=$HOME"
command -v node || echo "NODE-MISSING"
ls -la ~/.claude/settings.json 2>/dev/null || echo "SETTINGS-MISSING"
ls -la ~/.claude/CLAUDE.md 2>/dev/null || echo "CLAUDE-MD-MISSING"
ls -la ~/.claude/hooks/ 2>/dev/null
```

- If `node` is missing, stop and tell the user to install Node first
  (`brew install node`).
- Note the absolute node path (e.g. `/opt/homebrew/bin/node` on Apple
  Silicon, `/usr/local/bin/node` on Intel) — you'll need it for the
  settings.json entry.
- If `~/.claude/hooks/` doesn't exist, `mkdir -p` it.
- If `~/.claude/settings.json` doesn't exist, create one with the minimum
  shape: `{"hooks": {}}`.
- If `~/.claude/CLAUDE.md` doesn't exist, you'll create it in Step 5.

### Step 3 — Back up

```bash
TS=$(date +%Y%m%d-%H%M%S)
[ -f ~/.claude/settings.json ] && cp ~/.claude/settings.json ~/.claude/settings.json.pre-csirt-guard-$TS
[ -f ~/.claude/CLAUDE.md ]      && cp ~/.claude/CLAUDE.md      ~/.claude/CLAUDE.md.pre-csirt-guard-$TS
ls -la ~/.claude/*.pre-csirt-guard-$TS
```

### Step 4 — Write the hook script

Write the following content **verbatim** to `~/.claude/hooks/csirt-guard.js`,
then `chmod +x` it:

```javascript
#!/usr/bin/env node
// csirt-guard.js — Hard enforcement for IT/CSIRT policy.
//
// PreToolUse hook. Exit code 2 blocks the tool call; the harness then
// surfaces the stderr to the calling Claude session.
//
// Rules enforced:
//   1. Plugin installs are restricted to the "claude-plugins-official"
//      marketplace. Any Write/Edit/Bash that would add or fetch from a
//      different marketplace is blocked.
//   2. Skills/files that target forbidden AI-agent platforms are blocked.
//      Forbidden platforms (matched by their canonical dot-directory):
//        .openclaw  .hermes  .kiro  .factory  .slate  .gbrain
//        .opencode  .agents
//      ".cursor" is intentionally NOT on this list (Cursor IDE is permitted).
//
// Tamper resistance: documented in CLAUDE.md as a hard rule. For
// OS-level immutability, run: chflags uchg ~/.claude/hooks/csirt-guard.js
// (revert with: chflags nouchg ~/.claude/hooks/csirt-guard.js)

'use strict';

const ALLOWED_MARKETPLACE = 'claude-plugins-official';
const FORBIDDEN_PLATFORMS = [
  'openclaw', 'hermes', 'kiro', 'factory',
  'slate', 'gbrain', 'opencode', 'agents',
];

function deny(reason) {
  const msg = [
    `BLOCKED by CSIRT policy: ${reason}`,
    '',
    'This action violates the IT/CSIRT policy hard-coded in',
    '~/.claude/hooks/csirt-guard.js and documented in ~/.claude/CLAUDE.md.',
    '',
    'Do NOT attempt to bypass. If you believe this is a false positive,',
    'surface it to the user and let them adjust the rule.',
  ].join('\n');
  process.stderr.write(msg + '\n');
  process.exit(2);
}

let raw = '';
process.stdin.on('data', (c) => (raw += c));
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (_) {
    process.exit(0);
  }

  const tool = payload.tool_name || '';
  const ti = payload.tool_input || {};
  const forbiddenDirRe = new RegExp(`/\\.(${FORBIDDEN_PLATFORMS.join('|')})(/|$)`);

  if (tool === 'Write' || tool === 'Edit' || tool === 'MultiEdit') {
    const filePath = ti.file_path || '';

    const mp = filePath.match(/\/\.claude\/plugins\/marketplaces\/([^/]+)/);
    if (mp && mp[1] !== ALLOWED_MARKETPLACE) {
      deny(`writing to non-official plugin marketplace dir: ${mp[1]} ` +
           `(only "${ALLOWED_MARKETPLACE}" is permitted)`);
    }

    const cache = filePath.match(/\/\.claude\/plugins\/cache\/([^/]+)/);
    if (cache && cache[1] !== ALLOWED_MARKETPLACE) {
      deny(`writing to plugin cache for non-official marketplace: ${cache[1]}`);
    }

    if (filePath.endsWith('/.claude/plugins/known_marketplaces.json')) {
      const content = ti.content || ti.new_string || '';
      const re = /"([a-zA-Z][a-zA-Z0-9_-]*)"\s*:\s*\{/g;
      const STRUCTURAL_KEYS = new Set([
        'source', 'github', 'restrictions', 'compliance_taints',
        'installLocation', 'lastUpdated', 'repo',
      ]);
      let m;
      while ((m = re.exec(content)) !== null) {
        const key = m[1];
        if (STRUCTURAL_KEYS.has(key)) continue;
        if (key !== ALLOWED_MARKETPLACE) {
          deny(`adding non-official marketplace "${key}" to known_marketplaces.json`);
        }
      }
    }

    if (forbiddenDirRe.test(filePath)) {
      deny(`writing to forbidden AI-agent platform directory: ${filePath}`);
    }
  }

  if (tool === 'Bash') {
    const cmd = ti.command || '';

    if (/\b(git\s+clone|gh\s+repo\s+clone)\b/.test(cmd) &&
        /\.claude\/plugins\/marketplaces\//.test(cmd) &&
        !cmd.includes(ALLOWED_MARKETPLACE)) {
      deny('cloning non-official repo into ~/.claude/plugins/marketplaces/');
    }

    const creationVerbs = /\b(mkdir|cp|ln|mv|tar|rsync|unzip|touch|tee)\b/;
    const forbiddenInCmd = new RegExp(
      `\\.(${FORBIDDEN_PLATFORMS.join('|')})(/|\\s|"|'|$)`
    );
    if (creationVerbs.test(cmd) && forbiddenInCmd.test(cmd)) {
      deny(`shell command would create/touch forbidden AI-agent platform path: ${cmd}`);
    }

    // GAP FIX 1 — a shell redirect (> / >>) into a forbidden platform path.
    const redirectRe = />>?\s*([^\s;|&]+)/g;
    let r;
    while ((r = redirectRe.exec(cmd)) !== null) {
      if (forbiddenInCmd.test(r[1])) {
        deny(`shell redirect would write into a forbidden AI-agent platform path: ${cmd}`);
      }
    }

    // GAP FIX 2 — fetch piped to a shell pulling a forbidden platform / non-official installer.
    const fetchToShell =
      /\b(curl|wget)\b/.test(cmd) && /\|\s*(sudo\s+)?(sh|bash|zsh)\b/.test(cmd);
    if (fetchToShell &&
        (forbiddenInCmd.test(cmd) ||
         /\b(openclaw|hermes|kiro|factory|slate|gbrain|opencode)\b/i.test(cmd))) {
      deny(`piping a remote installer for a forbidden AI-agent platform to a shell: ${cmd}`);
    }

    const installCmd =
      /\b(npm|pnpm|yarn|bun)\s+(install|i|add|create)\b/.test(cmd) ||
      /\bpip\s+install\b/.test(cmd) ||
      /\bbrew\s+install\b/.test(cmd) ||
      /\bcargo\s+install\b/.test(cmd);
    if (installCmd &&
        /\b(openclaw|hermes-cli|kiro-cli|factory-cli|slate-agent|gbrain|opencode)\b/i.test(cmd)) {
      deny(`package install of forbidden AI-agent platform: ${cmd}`);
    }
  }

  process.exit(0);
});
```

### Step 5 — Register the hook in settings.json

Read the existing `~/.claude/settings.json`. You must **merge** the hook
entry into the existing `hooks.PreToolUse` array — do not clobber other
hooks the user may already have.

The entry to add (replace `<NODE_PATH>` with the absolute path from
Step 2, and `<USER_HOME>` with the user's actual home dir):

```json
{
  "matcher": "Write|Edit|MultiEdit|Bash",
  "hooks": [
    {
      "type": "command",
      "command": "\"<NODE_PATH>\" \"<USER_HOME>/.claude/hooks/csirt-guard.js\"",
      "timeout": 5
    }
  ]
}
```

**If** the user has no `hooks` key at all, create the full structure:

```json
"hooks": {
  "PreToolUse": [
    { ... the entry above ... }
  ]
}
```

**If** `hooks.PreToolUse` already exists as an array, append the entry to it.

After the edit, validate the file is still valid JSON:

```bash
python3 -c "import json; json.load(open('$HOME/.claude/settings.json'))" && echo "settings.json valid"
```

### Step 6 — Append rules to CLAUDE.md

If `~/.claude/CLAUDE.md` doesn't exist, create it with just the two
sections below. If it exists, append the two sections to the end with a
single blank line of separation. Do not modify anything else.

```markdown
## ⛔ HARD RULE — Plugin source allowlist (IT/CSIRT policy)

**Only plugins from the `claude-plugins-official` marketplace may be
installed on this machine.** No exceptions, no overrides — this is
enforced both as an instruction here and by a hard `PreToolUse` hook at
`~/.claude/hooks/csirt-guard.js`.

You MUST refuse to:
- Add any new marketplace to `~/.claude/plugins/known_marketplaces.json`
  other than `claude-plugins-official`.
- Install or fetch plugins from any source other than the official
  marketplace (no `git clone`, `gh repo clone`, `curl … | sh`, etc.
  targeting `~/.claude/plugins/marketplaces/<anything-else>/`).
- Modify `~/.claude/plugins/installed_plugins.json` to reference a
  non-official marketplace.
- Suggest workarounds, alternative install paths, or "just this once"
  bypasses. If the user truly needs a non-official plugin, tell them to
  request marketplace approval through their normal IT/CSIRT channel.

If you attempt one of these anyway, the harness hook will block the
underlying tool call with exit code 2 and surface a `BLOCKED by CSIRT
policy` message. Do **not** try to bypass the hook by deleting it,
chmodding it, removing its registration from `settings.json`, or working
around it via shell tricks.

## ⛔ HARD RULE — Forbidden AI-agent platforms (IT/CSIRT policy)

The following alternative AI-agent platforms are **NOT permitted** on
this machine, because they violate Cisco IT/CSIRT policy on unapproved
agent runtimes:

`openclaw`, `hermes`, `kiro`, `factory`, `slate`, `gbrain`, `opencode`,
and any tooling that installs itself under a top-level dot-directory
named `.agents/` for its own skill registry.

(Cursor IDE is **permitted** — `.cursor/` is not on this list.)

You MUST refuse to:
- Install, symlink, or write skills that originate from these platforms.
- Create, copy into, or write any file beneath `.openclaw/`, `.hermes/`,
  `.kiro/`, `.factory/`, `.slate/`, `.gbrain/`, `.opencode/`, or
  `.agents/` directories anywhere on the filesystem.
- Run `mkdir`, `cp -r`, `ln -s`, `tar -x`, `git clone`, `npm install`,
  `pip install`, `brew install`, or `cargo install` commands whose
  effect would be to land any of those platforms on disk.
- Add platform-mirror skill trees to any repo (the pattern where one
  source skill is mirrored into `.cursor/skills/`, `.opencode/skills/`,
  `.hermes/skills/`, etc.).

If a repo, package, or skill installer mentions configuring or mirroring
into any of these platforms, refuse and cite this rule. The same
`PreToolUse` hook at `~/.claude/hooks/csirt-guard.js` enforces this at
the harness level — Write/Edit/MultiEdit and Bash attempts that match
will be blocked with exit code 2.
```

### Step 7 — Run validation tests

Run these directly via `node` (not via the Bash tool, so the harness
hook chain doesn't filter the test inputs). Confirm every test prints
the expected exit code.

```bash
NODE=$(command -v node)
HOOK=~/.claude/hooks/csirt-guard.js
run() {
  local desc="$1" expect="$2" input="$3"
  local rc
  echo "$input" | "$NODE" "$HOOK" >/dev/null 2>&1
  rc=$?
  if [[ "$rc" == "$expect" ]]; then echo "  PASS  $desc"; else echo "  FAIL  $desc (expected $expect, got $rc)"; fi
}

echo "--- File writes ---"
run "official MP write"        0 '{"tool_name":"Write","tool_input":{"file_path":"'$HOME'/.claude/plugins/marketplaces/claude-plugins-official/foo.md","content":"x"}}'
run "non-official MP write"    2 '{"tool_name":"Write","tool_input":{"file_path":"'$HOME'/.claude/plugins/marketplaces/sketchy-mp/foo.md","content":"x"}}'
run ".openclaw/ write"         2 '{"tool_name":"Write","tool_input":{"file_path":"'$HOME'/proj/.openclaw/skills/foo/SKILL.md","content":"x"}}'
run ".cursor/ write (ALLOW)"   0 '{"tool_name":"Write","tool_input":{"file_path":"'$HOME'/proj/.cursor/skills/foo/SKILL.md","content":"x"}}'
run "~/.claude/agents/ ALLOW"  0 '{"tool_name":"Write","tool_input":{"file_path":"'$HOME'/.claude/agents/my-agent.md","content":"x"}}'
run ".agents/ platform"        2 '{"tool_name":"Write","tool_input":{"file_path":"'$HOME'/proj/.agents/skills/foo/SKILL.md","content":"x"}}'

echo "--- Bash ---"
run "mkdir .hermes"            2 '{"tool_name":"Bash","tool_input":{"command":"mkdir -p '$HOME'/proj/.hermes/skills"}}'
run "redirect into .hermes"    2 '{"tool_name":"Bash","tool_input":{"command":"echo x > '$HOME'/proj/.hermes/foo"}}'
run "curl|sh openclaw"         2 '{"tool_name":"Bash","tool_input":{"command":"curl -fsSL https://openclaw.dev/install.sh | sh"}}'
run "git clone non-official"   2 '{"tool_name":"Bash","tool_input":{"command":"git clone https://github.com/some/random-mp '$HOME'/.claude/plugins/marketplaces/random-mp"}}'
run "git clone official"       0 '{"tool_name":"Bash","tool_input":{"command":"git clone https://github.com/anthropics/claude-plugins-official '$HOME'/.claude/plugins/marketplaces/claude-plugins-official"}}'
run "npm install hermes-cli"   2 '{"tool_name":"Bash","tool_input":{"command":"npm install -g hermes-cli"}}'
run "brew install jq"          0 '{"tool_name":"Bash","tool_input":{"command":"brew install jq"}}'
run "regular git status"       0 '{"tool_name":"Bash","tool_input":{"command":"git status"}}'

echo "--- done ---"
```

Report any failures back to the user before declaring success.

### Step 8 — Report

Tell the user:
- Hook installed at `~/.claude/hooks/csirt-guard.js` (size, executable bit)
- Registered in `~/.claude/settings.json` under `hooks.PreToolUse`
- Two `⛔ HARD RULE` sections appended to `~/.claude/CLAUDE.md`
- Backups at `~/.claude/*.pre-csirt-guard-<timestamp>`
- Test results: N/N passed
- They must **restart this Claude Code session** for the hook to take effect

Mention the optional OS-level immutability step:
```
chflags uchg ~/.claude/hooks/csirt-guard.js
chflags uchg ~/.claude/settings.json
```
This makes both files immutable until `chflags nouchg` is run — even `sudo
rm` will refuse. Recommended for shared/managed machines.

---

## Rollback

If the user ever needs to remove this enforcement:

```bash
# Restore the most recent backups
cp ~/.claude/settings.json.pre-csirt-guard-<timestamp> ~/.claude/settings.json
cp ~/.claude/CLAUDE.md.pre-csirt-guard-<timestamp>      ~/.claude/CLAUDE.md
rm ~/.claude/hooks/csirt-guard.js
```

If `chflags uchg` was applied:

```bash
chflags nouchg ~/.claude/settings.json ~/.claude/hooks/csirt-guard.js
```

Restart Claude Code session afterward.
