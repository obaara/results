#!/usr/bin/env python3
"""
Deployment script for the Nigerian School Result Portal
Handles both backend and frontend deployment
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

class SchoolPortalDeployer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backend_dir = self.project_root / "school_result_api"
        self.frontend_dir = self.project_root / "school_result_frontend"
        self.deployment_dir = self.project_root / "deployment"
        
    def setup_deployment_directory(self):
        """Create and setup deployment directory"""
        print("📁 Setting up deployment directory...")
        
        # Create deployment directory
        self.deployment_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.deployment_dir / "backend").mkdir(exist_ok=True)
        (self.deployment_dir / "frontend").mkdir(exist_ok=True)
        (self.deployment_dir / "static").mkdir(exist_ok=True)
        (self.deployment_dir / "logs").mkdir(exist_ok=True)
        
        print("✅ Deployment directory setup complete")
    
    def build_frontend(self):
        """Build React frontend for production"""
        print("🔨 Building React frontend...")
        
        try:
            # Change to frontend directory and build
            os.chdir(self.frontend_dir)
            result = subprocess.run(["pnpm", "run", "build"], check=True, capture_output=True, text=True)
            print("✅ Frontend build successful")
            
            # Copy built files to deployment directory
            dist_dir = self.frontend_dir / "dist"
            if dist_dir.exists():
                shutil.copytree(dist_dir, self.deployment_dir / "frontend", dirs_exist_ok=True)
                print("✅ Frontend files copied to deployment directory")
            else:
                raise Exception("Build directory not found")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Frontend build failed: {e}")
            print(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            print(f"❌ Frontend deployment failed: {e}")
            return False
        
        return True
    
    def prepare_backend(self):
        """Prepare backend for deployment"""
        print("🔧 Preparing backend for deployment...")
        
        try:
            # Copy backend source files
            backend_src = self.backend_dir / "src"
            deployment_backend = self.deployment_dir / "backend"
            
            if backend_src.exists():
                shutil.copytree(backend_src, deployment_backend / "src", dirs_exist_ok=True)
            
            # Copy configuration files
            files_to_copy = ["requirements.txt", "init_db.py"]
            for file_name in files_to_copy:
                src_file = self.backend_dir / file_name
                if src_file.exists():
                    shutil.copy2(src_file, deployment_backend / file_name)
            
            # Create production configuration
            self.create_production_config()
            
            # Create deployment scripts
            self.create_deployment_scripts()
            
            print("✅ Backend preparation complete")
            return True
            
        except Exception as e:
            print(f"❌ Backend preparation failed: {e}")
            return False
    
    def create_production_config(self):
        """Create production configuration files"""
        print("⚙️ Creating production configuration...")
        
        # Create production environment file
        env_content = """# Production Environment Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-production-key-change-this
DATABASE_URL=sqlite:///school_portal.db
JWT_SECRET_KEY=your-jwt-secret-key-change-this
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
"""
        
        with open(self.deployment_dir / "backend" / ".env.production", "w") as f:
            f.write(env_content)
        
        # Create production main.py
        prod_main_content = """#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from src.main import create_app

# Load production environment
from dotenv import load_dotenv
load_dotenv('.env.production')

app = create_app('production')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
"""
        
        with open(self.deployment_dir / "backend" / "app.py", "w") as f:
            f.write(prod_main_content)
        
        print("✅ Production configuration created")
    
    def create_deployment_scripts(self):
        """Create deployment and management scripts"""
        print("📜 Creating deployment scripts...")
        
        # Create start script
        start_script = """#!/bin/bash
# Start script for Nigerian School Result Portal

echo "🚀 Starting Nigerian School Result Portal..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Initialize database if needed
if [ ! -f "school_portal.db" ]; then
    echo "🗄️ Initializing database..."
    python init_db.py
fi

# Start the application
echo "🌟 Starting application on port ${PORT:-5000}..."
python app.py
"""
        
        with open(self.deployment_dir / "start.sh", "w") as f:
            f.write(start_script)
        os.chmod(self.deployment_dir / "start.sh", 0o755)
        
        # Create stop script
        stop_script = """#!/bin/bash
# Stop script for Nigerian School Result Portal

echo "🛑 Stopping Nigerian School Result Portal..."

# Find and kill the process
PID=$(ps aux | grep 'python app.py' | grep -v grep | awk '{print $2}')
if [ ! -z "$PID" ]; then
    kill $PID
    echo "✅ Application stopped (PID: $PID)"
else
    echo "ℹ️ Application is not running"
fi
"""
        
        with open(self.deployment_dir / "stop.sh", "w") as f:
            f.write(stop_script)
        os.chmod(self.deployment_dir / "stop.sh", 0o755)
        
        # Create status script
        status_script = """#!/bin/bash
# Status script for Nigerian School Result Portal

echo "📊 Nigerian School Result Portal Status"
echo "======================================"

# Check if process is running
PID=$(ps aux | grep 'python app.py' | grep -v grep | awk '{print $2}')
if [ ! -z "$PID" ]; then
    echo "✅ Status: RUNNING (PID: $PID)"
    echo "🌐 URL: http://localhost:${PORT:-5000}"
else
    echo "❌ Status: STOPPED"
fi

# Check database
if [ -f "backend/school_portal.db" ]; then
    echo "🗄️ Database: EXISTS"
else
    echo "❌ Database: NOT FOUND"
fi

# Check log files
if [ -d "logs" ]; then
    echo "📝 Logs: Available in logs/ directory"
else
    echo "📝 Logs: No log directory found"
fi
"""
        
        with open(self.deployment_dir / "status.sh", "w") as f:
            f.write(status_script)
        os.chmod(self.deployment_dir / "status.sh", 0o755)
        
        print("✅ Deployment scripts created")
    
    def create_documentation(self):
        """Create deployment documentation"""
        print("📚 Creating deployment documentation...")
        
        readme_content = """# Nigerian School Result Portal - Deployment

## Overview
This is the production deployment package for the Nigerian School Result Portal, a comprehensive result management system for primary and secondary schools.

## Features
- ✅ Admin Panel for school management
- ✅ Teacher Portal for result entry
- ✅ Student Portal for viewing results
- ✅ Parent Portal for monitoring progress
- ✅ Automated result computation and grading
- ✅ Professional PDF report generation
- ✅ Role-based security and authentication
- ✅ Performance analytics and insights

## Quick Start

### 1. Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- 2GB RAM minimum
- 1GB disk space

### 2. Installation
```bash
# Extract the deployment package
cd school_result_portal_deployment

# Make scripts executable
chmod +x *.sh

# Start the application
./start.sh
```

### 3. Access the Application
- **Web Interface**: http://localhost:5000
- **API Documentation**: http://localhost:5000/api/info

### 4. Default Login Credentials
```
Super Admin:
  Username: superadmin
  Password: admin123

School Admin:
  Username: schooladmin  
  Password: admin123

Teacher:
  Username: teacher1
  Password: teacher123

Student:
  Username: student1
  Password: student123

Parent:
  Username: parent1
  Password: parent123
```

## Management Commands

### Start the Application
```bash
./start.sh
```

### Stop the Application
```bash
./stop.sh
```

### Check Status
```bash
./status.sh
```

## Configuration

### Environment Variables
Edit `backend/.env.production` to configure:
- Database settings
- Email configuration
- Security keys
- Application settings

### Database
The application uses SQLite by default. For production, consider:
- PostgreSQL for better performance
- MySQL for compatibility
- Regular backups

## File Structure
```
deployment/
├── backend/           # Backend API files
├── frontend/          # Built React frontend
├── logs/             # Application logs
├── start.sh          # Start script
├── stop.sh           # Stop script
├── status.sh         # Status check script
└── README.md         # This file
```

## Security Considerations
1. **Change Default Passwords**: Update all default passwords before production use
2. **Environment Variables**: Set secure values for SECRET_KEY and JWT_SECRET_KEY
3. **Database Security**: Use proper database credentials and encryption
4. **HTTPS**: Configure SSL/TLS for production deployment
5. **Firewall**: Restrict access to necessary ports only

## Backup and Maintenance
1. **Database Backup**: Regularly backup the database file
2. **Log Rotation**: Monitor and rotate log files
3. **Updates**: Keep dependencies updated for security
4. **Monitoring**: Monitor application performance and errors

## Troubleshooting

### Application Won't Start
1. Check Python version: `python3 --version`
2. Check dependencies: `pip list`
3. Check logs in `logs/` directory
4. Verify database exists: `ls backend/school_portal.db`

### Cannot Access Web Interface
1. Check if application is running: `./status.sh`
2. Verify port is not blocked by firewall
3. Check application logs for errors

### Database Issues
1. Reinitialize database: `cd backend && python init_db.py`
2. Check database permissions
3. Verify disk space availability

## Support
For technical support and documentation:
- Check the application logs
- Review the API documentation at /api/info
- Contact your system administrator

## Version Information
- **Version**: 1.0.0
- **Build Date**: """ + str(subprocess.check_output(['date'], text=True).strip()) + """
- **Python Version**: """ + sys.version.split()[0] + """

---
© 2025 Nigerian School Result Portal. All rights reserved.
"""
        
        with open(self.deployment_dir / "README.md", "w") as f:
            f.write(readme_content)
        
        print("✅ Documentation created")
    
    def deploy(self, include_frontend=True, include_backend=True):
        """Main deployment function"""
        print("🚀 Starting deployment of Nigerian School Result Portal...")
        print("=" * 60)
        
        success = True
        
        # Setup deployment directory
        self.setup_deployment_directory()
        
        # Build and deploy frontend
        if include_frontend:
            if not self.build_frontend():
                success = False
        
        # Prepare backend
        if include_backend:
            if not self.prepare_backend():
                success = False
        
        # Create documentation
        self.create_documentation()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 Deployment completed successfully!")
            print(f"📁 Deployment files are in: {self.deployment_dir}")
            print("\n📋 Next steps:")
            print("1. cd deployment")
            print("2. ./start.sh")
            print("3. Open http://localhost:5000 in your browser")
            print("\n🔐 Default login: superadmin / admin123")
        else:
            print("\n" + "=" * 60)
            print("❌ Deployment failed! Please check the errors above.")
        
        return success

def main():
    parser = argparse.ArgumentParser(description="Deploy Nigerian School Result Portal")
    parser.add_argument("--frontend-only", action="store_true", help="Deploy frontend only")
    parser.add_argument("--backend-only", action="store_true", help="Deploy backend only")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    args = parser.parse_args()
    
    # Determine what to deploy
    include_frontend = not args.backend_only
    include_backend = not args.frontend_only
    
    # Create deployer and run deployment
    deployer = SchoolPortalDeployer(args.project_root)
    success = deployer.deploy(include_frontend, include_backend)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

