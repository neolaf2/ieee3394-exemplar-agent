# Meta Business API Setup Guide

This guide walks through setting up a Meta Business App and obtaining the credentials needed for WhatsApp channel configuration.

## Prerequisites

1. **Meta Business Account**
   - Go to: https://business.facebook.com/
   - Create a business account if you don't have one
   - Verify your business identity (required for WhatsApp)

2. **WhatsApp Business Account**
   - Must be associated with your Meta Business Account
   - Can be created during app setup

3. **Phone Number**
   - A phone number that isn't already registered with WhatsApp
   - Can be a mobile or landline number
   - Must be able to receive SMS or voice calls for verification

## Step-by-Step Setup

### Step 1: Create a Meta App

1. Go to Meta Developer Dashboard: https://developers.facebook.com/apps

2. Click **"Create App"**

3. Select **"Business"** as the app type

4. Fill in app details:
   - **App Name**: Choose a name (e.g., "IEEE 3394 Agent WhatsApp")
   - **App Contact Email**: Your email address
   - **Business Account**: Select your Meta Business Account

5. Click **"Create App"**

6. You'll be redirected to the app dashboard

### Step 2: Add WhatsApp Product

1. In the app dashboard, find **"Add Products to Your App"**

2. Locate **"WhatsApp"** and click **"Set Up"**

3. Follow the WhatsApp setup wizard:
   - Select or create a WhatsApp Business Account
   - Select or add a phone number
   - Verify the phone number (via SMS or voice call)

4. Once setup is complete, you'll see the WhatsApp API Setup page

### Step 3: Obtain App ID and App Secret

1. In the left sidebar, go to **Settings → Basic**

2. Find your credentials:
   - **App ID**: A numeric string (e.g., `123456789012345`)
   - **App Secret**: Click **"Show"** to reveal (e.g., `abc123def456...`)

3. **⚠️ IMPORTANT**: Keep the App Secret secure! Never commit it to version control.

4. Copy both values - you'll need them for configuration

### Step 4: Obtain Phone Number ID

1. In the left sidebar, go to **WhatsApp → API Setup**

2. Under **"Send and receive messages"**, find:
   - **Phone Number ID**: A numeric string (e.g., `109876543210987`)
   - **WhatsApp Business Account ID**: Another numeric string

3. Copy both values

### Step 5: Generate Verify Token

The verify token is used for webhook verification. Generate a secure random string:

```bash
openssl rand -hex 32
```

Example output: `a3f8e9c1b2d4f5a6e8c9d1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2`

Save this token - you'll use it both in agent configuration and Meta webhook setup.

### Step 6: Determine Webhook URL

Your webhook URL is where Meta will send WhatsApp events.

**Production:**
```
https://your-domain.com/api/whatsapp/webhook
```

**Local Development (using ngrok):**

1. Install ngrok: https://ngrok.com/download

2. Start your agent locally:
   ```bash
   uv run python -m ieee3394_agent --channel whatsapp
   ```

3. Start ngrok tunnel:
   ```bash
   ngrok http 8000
   ```

4. Use the ngrok HTTPS URL:
   ```
   https://abc123.ngrok.io/api/whatsapp/webhook
   ```

### Step 7: Configure Webhook in Meta Dashboard

**⚠️ NOTE:** Do this AFTER running the agent configuration script, as the agent needs to be running to verify the webhook.

1. In Meta Developer Dashboard, go to **WhatsApp → Configuration**

2. In the **Webhook** section, click **"Edit"**

3. Enter:
   - **Callback URL**: Your webhook URL from Step 6
   - **Verify Token**: The token you generated in Step 5

4. Click **"Verify and Save"**

   Meta will send a GET request to your webhook with:
   ```
   GET /api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=XXXXX&hub.verify_token=YOUR_TOKEN
   ```

   Your agent must respond with the `hub.challenge` value.

5. If verification succeeds, you'll see a green checkmark ✓

### Step 8: Subscribe to Webhook Fields

1. In the **Webhook fields** section, click **"Manage"**

2. Subscribe to these fields:
   - **messages** (required) - Incoming messages
   - **message_status** (optional) - Delivery receipts

3. Click **"Save"**

### Step 9: Test the Connection

1. Send a test message to your WhatsApp Business number:
   ```
   Hello, this is a test message
   ```

2. Check your agent logs for the incoming message:
   ```
   [INFO] WhatsApp message received: {message_id: ..., from: +1234567890, text: "Hello..."}
   ```

3. The agent should respond if configured to do so

## Credential Summary

After completing these steps, you should have:

| Credential | Example | Where to Find |
|------------|---------|---------------|
| **App ID** | `123456789012345` | Settings → Basic |
| **App Secret** | `abc123def456...` | Settings → Basic → Show |
| **Phone Number ID** | `109876543210987` | WhatsApp → API Setup |
| **Business Account ID** | `987654321098765` | WhatsApp → API Setup |
| **Verify Token** | `a3f8e9c1b2d4f5a6...` | You generate this |
| **Webhook URL** | `https://your-domain.com/api/whatsapp/webhook` | Your server |

## Rate Limits and Quotas

**Meta enforces rate limits and messaging quotas:**

1. **Rate Limits**:
   - 80 messages per second per phone number
   - 250 messages per second per app
   - Violations result in temporary blocking

2. **Messaging Quotas** (daily limits):
   - Tier 1 (new): 1,000 unique conversations/day
   - Tier 2: 10,000 unique conversations/day
   - Tier 3: 100,000 unique conversations/day
   - Unlimited: Request from Meta

3. **Quality Rating**:
   - Must maintain "High" or "Medium" quality rating
   - Low quality rating reduces messaging limits
   - Based on user blocks, reports, and Meta policy violations

4. **Business Verification**:
   - Unverified businesses are limited to Tier 1
   - Verified businesses can reach higher tiers

## Permissions and Access

**App Permissions** (automatically granted):
- `whatsapp_business_management`: Manage WhatsApp Business resources
- `whatsapp_business_messaging`: Send messages

**User Permissions** (for human users):
- Must be admin or developer of the app
- Must have access to the WhatsApp Business Account

## Troubleshooting

### Error: "App is not approved for WhatsApp Business"

**Solution**: Submit app for review if using advanced features. Basic messaging works without review in development mode.

### Error: "Phone number is already registered"

**Solution**: The phone number is already used by another WhatsApp account. Use a different number or unregister the existing account.

### Error: "Business Account is not verified"

**Solution**: Complete Meta Business Verification:
- Go to https://business.facebook.com/settings/security
- Click "Start Verification"
- Provide business documents (varies by region)

### Error: "Webhook verification failed"

**Possible causes**:
1. Webhook URL is not publicly accessible
2. Verify token doesn't match
3. Agent is not running
4. Firewall blocking Meta's servers

**Solutions**:
1. Use ngrok for local testing
2. Double-check verify token matches exactly
3. Ensure agent is running and listening
4. Check firewall rules

### Error: "Cannot send message: quality rating too low"

**Solution**:
- Review recent messages for policy violations
- Improve message quality and relevance
- Reduce spam complaints
- Wait for quality rating to recover

## Security Best Practices

1. **App Secret Protection**:
   - Never commit to version control
   - Store in environment variables or encrypted storage
   - Rotate periodically

2. **Webhook Security**:
   - Always use HTTPS
   - Validate webhook signatures (optional but recommended)
   - Verify requests come from Meta's IP ranges

3. **Access Control**:
   - Limit who has access to Meta Developer Dashboard
   - Use separate apps for development and production
   - Enable Two-Factor Authentication on Meta account

4. **Monitoring**:
   - Monitor webhook logs for unusual activity
   - Set up alerts for failed authentications
   - Review message logs regularly

## Additional Resources

- **Meta WhatsApp Cloud API Docs**: https://developers.facebook.com/docs/whatsapp/cloud-api
- **API Reference**: https://developers.facebook.com/docs/whatsapp/cloud-api/reference
- **Webhooks Guide**: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
- **Message Templates**: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates
- **Business Verification**: https://www.facebook.com/business/help/2058515294227817
- **Meta Business Help Center**: https://www.facebook.com/business/help

## Quick Reference Commands

```bash
# Generate verify token
openssl rand -hex 32

# Start local agent
uv run python -m ieee3394_agent --channel whatsapp --port 8000

# Start ngrok tunnel
ngrok http 8000

# Test webhook verification
curl -X GET "https://your-domain.com/api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"

# Validate credentials
uv run python .claude/skills/whatsapp-config/scripts/validate_whatsapp_creds.py \
    --app-id YOUR_APP_ID \
    --app-secret YOUR_APP_SECRET \
    --phone-id YOUR_PHONE_ID \
    --business-id YOUR_BUSINESS_ID

# Configure agent
uv run python .claude/skills/whatsapp-config/scripts/configure_whatsapp.py \
    --app-id YOUR_APP_ID \
    --app-secret YOUR_APP_SECRET \
    --phone-id YOUR_PHONE_ID \
    --business-id YOUR_BUSINESS_ID \
    --verify-token YOUR_VERIFY_TOKEN \
    --webhook-url https://your-domain.com/api/whatsapp/webhook
```

## Support

If you encounter issues not covered in this guide:

1. Check Meta's status page: https://developers.facebook.com/status/
2. Review Meta Developer Community: https://developers.facebook.com/community/
3. Contact Meta Business Support (for verified businesses)
4. Review agent logs for detailed error messages
