# WhatsApp Webhook Troubleshooting Guide

This guide helps diagnose and fix common WhatsApp webhook issues.

## Webhook Verification Process

When you configure a webhook in Meta Developer Dashboard, Meta performs this verification:

1. **GET Request**: Meta sends a GET request to your webhook URL:
   ```
   GET /api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=XXXXX&hub.verify_token=YOUR_TOKEN
   ```

2. **Expected Response**: Your endpoint must:
   - Verify `hub.verify_token` matches your configured token
   - Return `hub.challenge` value as plain text
   - Return HTTP 200 status code

3. **Success**: If verification succeeds, Meta displays a green checkmark and starts sending events

## Common Issues and Solutions

### Issue 1: "Webhook Verification Failed"

**Symptoms:**
- Meta displays error: "The URL couldn't be validated"
- No verification request appears in agent logs

**Possible Causes:**

#### 1.1 URL Not Publicly Accessible

The webhook URL must be reachable from Meta's servers.

**Solution for Production:**
```bash
# Test public accessibility
curl -X GET "https://your-domain.com/api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"

# Expected response: "test"
```

**Solution for Local Development:**

Use ngrok to create a public tunnel:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start your agent
uv run python -m ieee3394_agent --channel whatsapp --port 8000

# In another terminal, start ngrok
ngrok http 8000

# Use the HTTPS URL provided by ngrok
# Example: https://abc123.ngrok.io
```

Update webhook URL in Meta Dashboard to: `https://abc123.ngrok.io/api/whatsapp/webhook`

#### 1.2 Verify Token Mismatch

The token in Meta Dashboard must exactly match the token in agent configuration.

**Check agent configuration:**
```bash
# View service principal config
cat .claude/principals/service_principals.json | grep -A 5 whatsapp
```

**Verify token in agent matches token in Meta Dashboard**

**Solution:**
- Regenerate verify token: `openssl rand -hex 32`
- Update agent configuration: Run configure_whatsapp.py with new token
- Update Meta Dashboard with same token

#### 1.3 Agent Not Running

The agent must be running when Meta performs verification.

**Check if agent is running:**
```bash
# Check process
ps aux | grep ieee3394_agent

# Check if port is listening
lsof -i :8000
```

**Solution:**
```bash
# Start the agent
uv run python -m ieee3394_agent --channel whatsapp --port 8000

# Verify webhook endpoint responds
curl -X GET "http://localhost:8000/api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"
```

#### 1.4 HTTPS Required

Meta requires HTTPS for webhooks (HTTP not accepted).

**Local Development Solution:**
- Use ngrok (provides HTTPS automatically)
- Use other tunneling services: localtunnel, serveo, etc.

**Production Solution:**
- Use Let's Encrypt for free SSL certificate
- Use cloud provider's SSL termination (AWS ALB, GCP Load Balancer, etc.)

#### 1.5 Firewall Blocking Meta's Servers

Your firewall might be blocking Meta's webhook verification requests.

**Meta's IP Ranges:**
```
173.252.88.0/21
185.60.216.0/22
```

**Solution:**
```bash
# Allow Meta's IPs (example for ufw)
sudo ufw allow from 173.252.88.0/21
sudo ufw allow from 185.60.216.0/22

# For production, use security groups or firewall rules specific to your infrastructure
```

### Issue 2: "Webhook Verified but No Messages Received"

**Symptoms:**
- Webhook verification succeeds
- Sending messages to WhatsApp number doesn't trigger webhook events
- No POST requests appear in agent logs

**Possible Causes:**

#### 2.1 Webhook Fields Not Subscribed

You must subscribe to the "messages" field to receive message events.

**Solution:**
1. Go to Meta Developer Dashboard → WhatsApp → Configuration
2. In the **Webhook fields** section, click "Manage"
3. Ensure **"messages"** is checked
4. Click "Save"

#### 2.2 Message Sent from Same Phone Number

You cannot send messages from the same phone number as your WhatsApp Business number.

**Solution:**
- Use a different phone number to test
- Ask a colleague or friend to send a test message

#### 2.3 Phone Number Not Active

The WhatsApp Business phone number might not be fully activated.

**Check phone number status:**
1. Go to Meta Developer Dashboard → WhatsApp → API Setup
2. Verify phone number shows "Active" status
3. Check quality rating (must be "High" or "Medium")

**Solution:**
- Complete phone number verification if pending
- Wait for Meta to approve phone number (can take 24-48 hours)

#### 2.4 Webhook URL Changed

If you changed the webhook URL after verification, Meta won't send events to the new URL.

**Solution:**
1. Update webhook URL in Meta Dashboard
2. Re-verify the webhook
3. Restart agent if needed

### Issue 3: "Messages Received but Agent Not Processing"

**Symptoms:**
- Webhook POST requests appear in agent logs
- Agent doesn't process or respond to messages

**Possible Causes:**

#### 3.1 Webhook Signature Validation Failing

If webhook signature validation is enabled, incorrect validation will reject messages.

**Check agent logs:**
```
grep -i "signature" /path/to/agent.log
```

**Solution:**
- Ensure App Secret in agent config matches Meta Dashboard
- Verify signature validation logic is correct
- Temporarily disable signature validation for testing (not recommended for production)

#### 3.2 Message Format Not Recognized

Agent might not recognize message format from Meta.

**Check agent logs for parsing errors:**
```
grep -i "error\|exception" /path/to/agent.log
```

**Solution:**
- Review Meta's webhook payload format: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
- Update message parsing logic in WhatsApp channel adapter
- Add logging for incoming webhook payloads

#### 3.3 Authentication/Authorization Failing

The sender might not be in the allowlist (if using whitelist mode).

**Check agent logs:**
```
grep -i "denied\|unauthorized" /path/to/agent.log
```

**Solution:**
- Add sender's phone number to credential bindings
- Check sender's principal has required permissions
- Review authentication logs

### Issue 4: "Rate Limit Exceeded"

**Symptoms:**
- Error: "Rate limit exceeded"
- Some messages not processed

**Possible Causes:**

Meta enforces rate limits:
- 80 messages/second per phone number
- 250 messages/second per app

**Solution:**
- Implement request queuing in agent
- Add exponential backoff for retries
- Distribute load across multiple phone numbers
- Contact Meta to increase limits for high-volume use cases

### Issue 5: "Webhook Timeout"

**Symptoms:**
- Error in Meta logs: "Webhook timed out"
- Messages eventually delivered but with delay

**Possible Causes:**

Meta expects webhook response within 20 seconds.

**Solution:**
- Process webhook requests asynchronously
- Return 200 OK immediately, process in background
- Optimize message processing pipeline

**Example async processing:**
```python
@app.post("/api/whatsapp/webhook")
async def webhook(request: Request):
    # Immediately acknowledge receipt
    data = await request.json()

    # Process asynchronously
    asyncio.create_task(process_webhook_data(data))

    # Return success immediately
    return {"status": "ok"}
```

## Diagnostic Commands

### Test Webhook Verification

```bash
# Test GET request (verification)
curl -X GET "https://your-domain.com/api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=test&hub.verify_token=YOUR_TOKEN"

# Expected response: "test"
```

### Test Webhook Endpoint Reachability

```bash
# From external server (or ask colleague)
curl -I https://your-domain.com/api/whatsapp/webhook

# Expected: HTTP 200 or 405 (Method Not Allowed for GET without query params)
```

### Check Agent Logs

```bash
# Real-time logs
tail -f /path/to/agent.log | grep -i whatsapp

# Recent webhook requests
grep "POST /api/whatsapp/webhook" /path/to/agent.log | tail -20

# Recent errors
grep -i "error\|exception" /path/to/agent.log | grep -i whatsapp | tail -20
```

### Check ngrok Status (Local Development)

```bash
# View ngrok dashboard
open http://localhost:4040

# Shows all HTTP requests to your tunnel
# Useful for debugging webhook verification
```

### Test Meta API Connectivity

```bash
# Get access token
curl "https://graph.facebook.com/v18.0/oauth/access_token?client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&grant_type=client_credentials"

# Test phone number endpoint
curl "https://graph.facebook.com/v18.0/YOUR_PHONE_ID?access_token=YOUR_ACCESS_TOKEN"
```

## Webhook Payload Examples

### Verification Request (GET)

```
GET /api/whatsapp/webhook?hub.mode=subscribe&hub.challenge=1234567890&hub.verify_token=your_token HTTP/1.1
Host: your-domain.com
User-Agent: facebookplatform/1.0 (+http://www.facebook.com)
```

**Expected Response:**
```
HTTP/1.1 200 OK
Content-Type: text/plain

1234567890
```

### Message Event (POST)

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "1234567890",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": {
            "name": "John Doe"
          },
          "wa_id": "1234567890"
        }],
        "messages": [{
          "from": "1234567890",
          "id": "wamid.XXX",
          "timestamp": "1234567890",
          "type": "text",
          "text": {
            "body": "Hello, agent!"
          }
        }]
      },
      "field": "messages"
    }]
  }]
}
```

**Expected Response:**
```
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "ok"}
```

## Meta Dashboard Webhook Logs

To view webhook delivery status in Meta Dashboard:

1. Go to **WhatsApp → Configuration**
2. Scroll to **Webhook** section
3. Click **"View Logs"** or **"Recent Deliveries"**
4. Review delivery status, response codes, and response times

## Getting Additional Help

If issues persist after trying these solutions:

1. **Enable Debug Logging:**
   ```bash
   export LOG_LEVEL=DEBUG
   uv run python -m ieee3394_agent --channel whatsapp
   ```

2. **Check Meta Developer Community:**
   - https://developers.facebook.com/community/

3. **Review Meta WhatsApp API Status:**
   - https://developers.facebook.com/status/

4. **Contact Meta Support:**
   - Available for businesses with Meta Business Verification

5. **Agent-Specific Support:**
   - Review agent documentation
   - Check GitHub issues (if applicable)
   - Contact agent maintainer

## Quick Reference Checklist

Before contacting support, verify:

- [ ] Webhook URL is publicly accessible
- [ ] HTTPS is enabled (required by Meta)
- [ ] Verify token in agent matches Meta Dashboard
- [ ] Agent is running and listening on correct port
- [ ] Firewall allows connections from Meta's IPs
- [ ] Webhook fields are subscribed in Meta Dashboard
- [ ] Phone number is active and verified
- [ ] App has WhatsApp product added
- [ ] App credentials (ID and Secret) are correct
- [ ] Webhook returns 200 OK within 20 seconds
- [ ] Agent logs show webhook requests
- [ ] Message format parsing is correct
- [ ] Authentication/authorization is configured

## Common Error Codes

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 400 | Bad Request | Check request format, verify webhook payload structure |
| 401 | Unauthorized | Check App Secret, verify signature validation |
| 403 | Forbidden | Check IP whitelist, verify permissions |
| 404 | Not Found | Verify webhook URL path is correct |
| 405 | Method Not Allowed | Verify endpoint accepts both GET and POST |
| 500 | Internal Server Error | Check agent logs for exceptions |
| 503 | Service Unavailable | Agent may be overloaded or down |
| 504 | Gateway Timeout | Webhook processing taking > 20 seconds |

## Testing Script

Save as `test_webhook.sh`:

```bash
#!/bin/bash

WEBHOOK_URL="https://your-domain.com/api/whatsapp/webhook"
VERIFY_TOKEN="your_verify_token"

echo "Testing WhatsApp Webhook..."
echo "=============================="
echo

echo "1. Testing verification (GET request)..."
CHALLENGE="test_challenge_12345"
response=$(curl -s -X GET "$WEBHOOK_URL?hub.mode=subscribe&hub.challenge=$CHALLENGE&hub.verify_token=$VERIFY_TOKEN")

if [ "$response" == "$CHALLENGE" ]; then
    echo "✓ Verification test passed"
else
    echo "✗ Verification test failed"
    echo "  Expected: $CHALLENGE"
    echo "  Got: $response"
fi

echo
echo "2. Testing webhook endpoint reachability..."
status_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK_URL")

if [ "$status_code" == "200" ] || [ "$status_code" == "400" ]; then
    echo "✓ Endpoint reachable (HTTP $status_code)"
else
    echo "✗ Endpoint not reachable (HTTP $status_code)"
fi

echo
echo "3. Testing HTTPS..."
if [[ $WEBHOOK_URL == https://* ]]; then
    echo "✓ Using HTTPS"
else
    echo "✗ Not using HTTPS (required by Meta)"
fi

echo
echo "=============================="
echo "Testing complete"
```

Run with:
```bash
chmod +x test_webhook.sh
./test_webhook.sh
```
