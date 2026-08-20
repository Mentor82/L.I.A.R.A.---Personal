#!/bin/bash
# Liara Frontend Auth - Quick Start Guide
# Run this script to complete the authentication setup

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Liara Frontend Auth - Quick Start${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Step 1: Add missing personalization function
echo -e "${YELLOW}Step 1: Adding personalization function to chat.py...${NC}"

PERSONALIZATION_FUNCTION='
def _get_personalized_context(user: User) -> str:
    """
    Generate personalized system prompt based on user.
    Mirko gets special warm personal treatment, others get friendly generic.
    """
    if user.username.lower() == "mirko":
        greeting = "Hi Mirko! Schön, dass du da bist."
        tone = "besonders persönlich und warmherzig"
        relationship = "Du kennst mich gut und weißt, wie ich ticke."
    else:
        name = user.full_name or user.username
        greeting = f"Hallo {name}! Schön, dich zu sehen."
        tone = "freundlich und hilfsbereit"
        relationship = "Wir arbeiten gemeinsam an deinen Zielen."
    
    return f"""{greeting} {relationship}

Deine Art: Sei {tone} im Umgang. Nutze \"du\" und bleibe natürlich."""
'

# Insert function after line 70 (after estimate_ram_needed function)
sed -i '70 a\
\
'"$PERSONALIZATION_FUNCTION"'' /opt/liara/app/api/routers/chat.py

echo -e "${GREEN}✓ Personalization function added${NC}"
echo ""

# Step 2: Restart backend
echo -e "${YELLOW}Step 2: Restarting backend...${NC}"
sudo pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 2

cd /opt/liara/app
/opt/liara/venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8100 > /tmp/liara_backend.log 2>&1 &

sleep 4

# Check if backend is running
if curl -s http://localhost:8100/ > /dev/null; then
    echo -e "${GREEN}✓ Backend restarted successfully${NC}"
else
    echo -e "${RED}✗ Backend failed to start - check /tmp/liara_backend.log${NC}"
    exit 1
fi

echo ""

# Step 3: Create Mirko user if doesn't exist
echo -e "${YELLOW}Step 3: Creating Mirko user account...${NC}"

MIRKO_RESPONSE=$(curl -s -X POST http://localhost:8100/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "mirko",
    "password": "mirko123",
    "email": "mirko@example.com",
    "full_name": "Mirko"
  }' 2>/dev/null || echo '{"detail":"User already exists"}')

if echo "$MIRKO_RESPONSE" | grep -q "access_token\|already exists"; then
    echo -e "${GREEN}✓ Mirko user ready${NC}"
    echo "  Username: mirko"
    echo "  Password: mirko123"
else
    echo -e "${RED}✗ Failed to create Mirko user${NC}"
    echo "$MIRKO_RESPONSE"
fi

echo ""

# Step 4: Start frontend
echo -e "${YELLOW}Step 4: Starting frontend dev server...${NC}"

cd /opt/liara/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install
fi

# Kill existing Vite server if running
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Start Vite in background
npm run dev > /tmp/liara_frontend.log 2>&1 &
VITE_PID=$!

sleep 3

# Check if Vite is running
if curl -s http://localhost:5173 > /dev/null; then
    echo -e "${GREEN}✓ Frontend server started (PID: $VITE_PID)${NC}"
    echo "  URL: http://localhost:5173"
else
    echo -e "${RED}✗ Frontend failed to start - check /tmp/liara_frontend.log${NC}"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Open browser: http://localhost:5173"
echo "2. Login as Mirko:"
echo "   Username: mirko"
echo "   Password: mirko123"
echo ""
echo "3. Or login as admin:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo -e "${YELLOW}What to expect:${NC}"
echo "• Mirko: Header shows 'Hi Mirko! 👋'"
echo "• Admin: Header shows 'Hallo, admin! 👋'"
echo "• Chat: Mirko gets warm personal responses"
echo "• Chat: Others get friendly helpful responses"
echo "• Logout: Click 'Abmelden' button in header"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "• Backend: /tmp/liara_backend.log"
echo "• Frontend: /tmp/liara_frontend.log"
echo ""
