#!/bin/bash
# Installation script for Praier

set -e

# Default installation directory
INSTALL_DIR="/opt/praier"
SERVICE_USER="praier"

echo "Installing Praier..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Create user for the service
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating user $SERVICE_USER..."
    useradd --system --home-dir "$INSTALL_DIR" --shell /bin/false "$SERVICE_USER"
fi

# Create installation directory
echo "Creating installation directory..."
mkdir -p "$INSTALL_DIR"
mkdir -p /var/log/praier

# Copy files
echo "Installing files..."
cp -r . "$INSTALL_DIR/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" /var/log/praier

# Create virtual environment
echo "Setting up Python environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Install systemd service
echo "Installing systemd service..."
cp scripts/praier.service /etc/systemd/system/
systemctl daemon-reload

echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit /etc/systemd/system/praier.service to configure your GitHub token and repositories"
echo "2. Enable the service: sudo systemctl enable praier"
echo "3. Start the service: sudo systemctl start praier"
echo "4. Check status: sudo systemctl status praier"
echo "5. View logs: sudo journalctl -u praier -f"