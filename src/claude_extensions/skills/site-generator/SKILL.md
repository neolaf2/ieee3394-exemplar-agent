---
name: site-generator
description: Generate static HTML pages for the IEEE 3394 website
triggers:
  - "generate site"
  - "update website"
  - "rebuild static pages"
  - "create html pages"
---

# Site Generator Skill

Generate static HTML content for the IEEE 3394 exemplar agent website.

## Your Role

You can generate and update HTML files for the agent's web presence, demonstrating P3394 capabilities through the website itself.

## Available Tools

Use these tools to build the site:

- **Read** - Read existing HTML templates
- **Write** - Create new HTML files
- **Edit** - Update existing pages
- **Bash** - Run build commands if needed

## Site Structure

```
static/
├── index.html          # Landing page
├── docs/              # Documentation
│   ├── index.html
│   ├── getting-started.html
│   ├── umf.html
│   └── channels.html
├── demo/              # Interactive demos
│   ├── index.html
│   └── chat.html
└── assets/
    ├── css/
    └── js/
```

## Content to Generate

### 1. Landing Page (index.html)

- Hero section explaining P3394
- Feature highlights (UMF, Channels, Discovery)
- Call-to-action (Try the chat, Read docs)
- Live agent status

### 2. Documentation Pages

Generate pages for:
- **Getting Started** - Quick intro, installation, first message
- **UMF Guide** - Message format, examples, best practices
- **Channel Adapters** - How to build adapters, examples
- **Agent Discovery** - Manifests, capability negotiation
- **API Reference** - Endpoints, parameters, responses

### 3. Demo Pages

- **Interactive Chat** - Live chat with the agent via P3394
- **Message Inspector** - View raw UMF messages
- **Multi-Channel Demo** - Same message through different channels

## Generation Process

1. **Understand requirements** - What pages are needed?
2. **Read existing content** - Check what's already there
3. **Generate HTML** - Create clean, semantic HTML5
4. **Use consistent styling** - Match existing theme
5. **Test accessibility** - Semantic HTML, proper headings
6. **Write files** - Save to appropriate locations

## HTML Guidelines

### Use Semantic HTML

```html
<article>
  <header>
    <h1>Universal Message Format</h1>
    <p class="subtitle">The heart of P3394</p>
  </header>

  <section>
    <h2>What is UMF?</h2>
    <p>...</p>
  </section>
</article>
```

### Include Meta Tags

```html
<meta name="description" content="IEEE P3394 Exemplar Agent">
<meta property="og:title" content="P3394 Standard">
<meta property="og:description" content="Universal agent interfaces">
```

### Use Tailwind CSS (already included)

```html
<div class="max-w-7xl mx-auto px-4 py-16">
  <h1 class="text-4xl font-bold mb-4">Title</h1>
  <p class="text-gray-600">Description</p>
</div>
```

## Example: Generate Documentation Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Universal Message Format - P3394</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow">
        <div class="max-w-7xl mx-auto px-4 py-3">
            <a href="/" class="text-xl font-bold text-blue-600">IEEE P3394</a>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto px-4 py-16">
        <article>
            <h1 class="text-4xl font-bold mb-4">Universal Message Format</h1>

            <section class="mb-8">
                <h2 class="text-2xl font-semibold mb-3">Overview</h2>
                <p class="text-gray-700 mb-4">
                    UMF (Universal Message Format) is the standardized message
                    structure for P3394 agent communication...
                </p>
            </section>

            <section class="mb-8">
                <h2 class="text-2xl font-semibold mb-3">Message Structure</h2>
                <pre class="bg-gray-100 p-4 rounded overflow-x-auto">
<code>{
  "id": "msg-123",
  "type": "request",
  "content": [...]
}</code></pre>
            </section>
        </article>
    </main>
</body>
</html>
```

## When to Use This Skill

- User asks to "generate the website"
- User wants to add new documentation
- User wants to update existing pages
- User requests demo pages

## Process

1. Ask user what content to generate (or use defaults)
2. Read any existing files that need updating
3. Generate clean, well-structured HTML
4. Write files to appropriate locations
5. Confirm what was created

## Important Notes

- Keep pages simple and fast-loading
- Ensure mobile responsiveness (Tailwind handles this)
- Use semantic HTML for accessibility
- Include code examples in documentation
- Make sure all links work
- Test in browser if possible
