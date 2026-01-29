Overview

1. **Capability Descriptor (CD) schema** (core abstraction)

2. Show how it fits into the **Agent Interface / Manifest (P3394-aligned)**

3. F**eature requirements** for

   * the **Agent SDK**

   * the **IEEE3394 exemplar agent**

---

# **1\. Agent Capability Descriptor (ACD)**

## **1.1 Core Definition**

An **Agent Capability Descriptor (ACD)** describes a unit of agent functionality that can be invoked, composed, delegated, or exposed, independent of how it is implemented.

Everything (skill, command, sub-agent, adapter, hook, function) is a **capability** with metadata.

---

## **1.2 Capability Descriptor Schema (Canonical)**

Below is a **normative JSON schema** (conceptual, not JSON-Schema-draft strict yet).

{  
  "capability\_id": "string",                
  "name": "string",  
  "version": "string",

  "description": "string",

  "kind": "atomic | composite | proxy | template",

  "execution": {  
    "substrate": "symbolic | llm | shell | agent | external\_service | transport",  
    "runtime": "string",  
    "entrypoint": "string"  
  },

  "invocation": {  
    "modes": \[  
      "direct",  
      "command",  
      "message",  
      "event",  
      "ui\_action"  
    \],  
    "command\_aliases": \["string"\]  
  },

  "exposure": {  
    "scope": "internal | agent | channel | human | public",  
    "channels": \["cli", "web", "slack", "email", "mcp"\]  
  },

  "permissions": {  
    "required": \["string"\],  
    "granted\_by\_default": false,  
    "danger\_level": "low | medium | high | critical"  
  },

  "inputs": {  
    "schema": "json-schema | reference",  
    "required": \["string"\]  
  },

  "outputs": {  
    "schema": "json-schema | reference"  
  },

  "dependencies": {  
    "capabilities": \["capability\_id"\],  
    "resources": \["filesystem", "network", "gpu"\]  
  },

  "lifecycle": {  
    "hooks": {  
      "pre\_invoke": \["capability\_id"\],  
      "post\_invoke": \["capability\_id"\],  
      "on\_error": \["capability\_id"\]  
    }  
  },

  "delegation": {  
    "allowed": true,  
    "creates\_subagent": false  
  },

  "audit": {  
    "log\_invocation": true,  
    "log\_inputs": false,  
    "log\_outputs": false  
  },

  "status": {  
    "enabled": true,  
    "mutable": true,  
    "signed": false  
  }  
}

This schema is intentionally **superset** and **orthogonal**:

* No “skill vs command vs sub-agent” branching

* All differences are metadata

---

## **2\. Integrating Capability Descriptors into the Agent Interface / Manifest**

## **2.1 Agent Manifest Extension (P3394-Compatible)**

The **Agent Manifest** becomes the *capability index*.

{  
  "agent\_id": "urn:agent:ieee:3394:exemplar",  
  "name": "IEEE3394 Exemplar Agent",  
  "version": "0.1.0",

  "capabilities": {  
    "registry": "inline | external",  
    "list": \[  
      "cap.help",  
      "cap.identify",  
      "cap.send\_umf",  
      "cap.cli.adapter",  
      "cap.skill.create",  
      "cap.subagent.create"  
    \]  
  },

  "channels": \[  
    {  
      "channel\_id": "cli",  
      "capabilities": \["cap.cli.adapter"\]  
    }  
  \],

  "policies": {  
    "capability\_mutation": "restricted",  
    "shell\_access": "scoped",  
    "llm\_required\_for": \[  
      "capability.create",  
      "delegation"  
    \]  
  }  
}

Key point:

**Channels do not define behavior — they expose capabilities.**  
---

## **2.2 Replacing Legacy Lists**

Old-style commands:

| Old Endpoint | New Interpretation |
| ----- | ----- |
| /listSkills | /listCapabilities?kind=composite |
| /listCommands | /listCapabilities?invocation=command |
| /listSubAgents | /listCapabilities?execution=agent |
| /listChannels | /listCapabilities?execution=transport |

This preserves backward compatibility while unifying semantics.

---

## **3\. Feature Requirements Derived from the Capability Model**

Now the important part: **what this forces the SDK and exemplar to implement**.

---

# **3.1 Agent SDK Feature Requirements**

### **FR-SDK-1: Unified Capability Registry (MANDATORY)**

The SDK MUST provide:

* a single **Capability Registry**

* CRUD operations on capability descriptors

* query by:

  * execution substrate

  * invocation mode

  * exposure scope

  * enabled/disabled status

No separate “skill registry”, “command registry”, etc.

---

### **FR-SDK-2: Capability Invocation Engine**

The SDK MUST:

* accept a capability ID

* validate permissions

* route execution based on execution.substrate

* enforce invocation mode constraints

This is the **core runtime**.

---

### **FR-SDK-3: LLM-Orchestrated Capability Creation**

The SDK MUST support:

* creating new capability descriptors at runtime

* via LLM-mediated meta-capabilities:

  * capability.create

  * capability.enable

  * capability.bind

LLM is REQUIRED for:

* composite capability creation

* sub-agent (proxy) capability creation

---

### **FR-SDK-4: Shell as Privileged Execution Substrate**

The SDK MUST:

* expose a **non-UMF internal shell interface**

* restrict it via:

  * capability permissions

  * OS-level sandboxing

* prevent direct shell exposure via channel adapters

Shell is treated as:

execution substrate, not a capability exposed to humans  
---

### **FR-SDK-5: Channel Adapters as Capability Providers**

Each channel adapter MUST:

* declare which **capabilities it realizes**

* declare supported invocation modes (e.g. ui\_action)

* reject unsupported capability projections

This is how A2UI fits cleanly.

---

### **FR-SDK-6: Audit & Governance Hooks**

The SDK MUST:

* log capability invocations

* support lifecycle hooks via capability descriptors

* support immutable (constitution-level) capabilities

---

# **3.2 IEEE3394 Exemplar Agent Requirements**

The exemplar is not “a demo” — it is **normative**.

### **FR-EX-1: Minimum Capability Set**

The exemplar MUST ship with:

| Capability | Purpose |
| ----- | ----- |
| cap.identify | Agent identity |
| cap.send\_umf | Canonical interface |
| cap.cli.adapter | Default channel |
| cap.capability.list | Introspection |
| cap.capability.create | Self-extension |
| cap.subagent.create | Delegation |
| cap.command.bind | Command creation |
| cap.hook.create | Lifecycle control |

---

### **FR-EX-2: CLI as Mandatory Capability**

The exemplar MUST:

* include CLI adapter capability

* allow full agent operation via CLI alone

* demonstrate OS-backed execution

---

### **FR-EX-3: Capability-Based A2UI Demonstration**

The exemplar SHOULD:

* demonstrate A2UI as a **capability projection**

* e.g. a UI capability rendered differently on:

  * CLI (prompt)

  * Web (button)

---

### **FR-EX-4: Capability Manifest as Ground Truth**

The exemplar MUST:

* generate its website / docs from the capability registry

* prove:

   “The agent describes itself truthfully.”

---

## **4\. Why This Matters (One Paragraph)**

By introducing a **Capability Descriptor**, you collapse:

* skills

* commands

* sub-agents

* adapters

* hooks

into a **single, composable abstraction** that:

* fits P3394 cleanly

* scales across SDKs

* enables governance

* makes exemplars authoritative

This is not just cleaner — it is **necessary** for standardization.

