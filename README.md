# 📧 Email-Attachments-Manager (SORT-E)

**Professional Desktop Email Management System with Advanced Attachment Organization**

A powerful, modern email management application built with PyQt5 that provides comprehensive email organization, advanced tagging, and intelligent attachment management for professionals and organizations.

## ✨ Key Features

- 🔐 **Secure Multi-User Dashboard** - Complete user authentication with email verification
- 📬 **Multi-Account Email Management** - Support for multiple IMAP email accounts
- 🏷️ **Smart Auto-Tagging System** - Custom rules with automatic attachment saving
- 📎 **Advanced Attachment Search** - Search across all attachment metadata
- ⚡ **Bulk Operations** - Mass email management and organization
- 🎨 **Modern UI** - Outlook-inspired professional interface
- 📊 **Analytics Dashboard** - Comprehensive email statistics and insights

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- MySQL Server
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/haiderali-dev/Email-Attachments-Manager-SORT-E.git
   cd email-attachments-manager
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   
   Create your environment file from the template:
   ```bash
   # Copy the template
   cp env_template.txt .env
   
   # Edit with your credentials
   nano .env  # or use your preferred editor
   ```

4. **Set up Database Credentials**
   
   Edit your `.env` file with your MySQL database credentials:
   ```env
   # Database Configuration
   DB_HOST=localhost
   DB_USER=your-username
   DB_PASSWORD=your-password
   DB_PORT=3306
   DB_NAME=email_manager
   ```

5. **Configure Email Verification**
   
   Set up SMTP credentials for user verification emails:
   ```env
   # Email Verification Configuration
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

## 🔧 Environment Configuration

### Required Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | MySQL server host | `localhost` |
| `DB_USER` | MySQL username | `root` |
| `DB_PASSWORD` | MySQL password | (empty) |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `email_manager` |
| `SMTP_SERVER` | SMTP server for verification | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `465` |
| `SMTP_USERNAME` | SMTP username | (required) |
| `SMTP_PASSWORD` | SMTP password/app password | (required) |

### Gmail Setup for Email Verification

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail"
3. **Use the App Password** in your `.env` file (not your regular password)

### Optional Application Settings

```env
# Application Settings
DEFAULT_IMAP_HOST=mail2.multinet.com.pk
SESSION_DAYS=90
REAL_TIME_MONITORING=true
MONITORING_INTERVAL=30
PROGRESSIVE_BATCH_SIZE=200
PROGRESSIVE_COMMIT_INTERVAL=100
```

## ⚙️ Configuration

### Database Setup

The application will automatically create the required database and tables on first run. Ensure your MySQL server is running and accessible with the credentials specified in your `.env` file.

### Email Verification Setup

For user registration verification emails, configure your SMTP settings in your `.env` file. The application supports:
- **Gmail**: Use App Passwords (recommended)
- **Outlook/Hotmail**: Use regular passwords
- **Custom SMTP**: Configure your own SMTP server

### Application Settings

The application uses a combination of:
- **Environment Variables** (`.env` file) - For sensitive credentials and core settings
- **Config File** (`config.json`) - For user preferences and UI settings

### Security Features

- **Environment Variables**: All sensitive data stored in `.env` file (not committed to git)
- **Password Encryption**: Email passwords encrypted with Fernet encryption
- **Auto-Generated Keys**: `secret.key` file auto-generated for encryption
- **User Isolation**: Complete data separation between dashboard users

## 📋 Usage

### First Time Setup

1. **Register Account**: Create a new user account with email verification
2. **Add Email Accounts**: Configure your IMAP email accounts
3. **Set Up Tags**: Create custom tags for email organization
4. **Configure Rules**: Set up auto-tagging rules with attachment saving

### Key Workflows

- **Email Management**: View, search, and organize emails across multiple accounts
- **Attachment Handling**: Search, view, and download attachments with custom paths
- **Bulk Operations**: Perform mass operations on emails and attachments
- **Analytics**: Monitor email statistics and usage patterns

## 🏗️ Architecture

Built with clean architecture principles:
- **Models**: Database entities and data structures
- **Views**: PyQt5 UI components organized by feature
- **Controllers**: Business logic and user interaction handling
- **Services**: External system interactions (IMAP, database, filesystem)
- **Workers**: Background processing for async operations

## 🔐 Security Features

- **Password Encryption**: bcrypt hashing with salt
- **Email Password Encryption**: Fernet symmetric encryption
- **Account Lockout**: 5-attempt limit with timeout
- **Session Management**: Configurable session duration
- **User Isolation**: Complete data separation between users

## 📊 Database Schema

The application uses a unified MySQL database with the following core tables:
- `dashboard_users` - User accounts and authentication
- `accounts` - Email account configurations
- `emails` - Email storage with metadata
- `tags` - User-defined tags
- `auto_tag_rules` - Custom tagging rules
- `attachments` - Attachment metadata and storage

## 🔍 Advanced Features

- **Smart Duplicate Prevention**: Avoids re-downloading existing emails/attachments
- **Real-time Monitoring**: Live email synchronization
- **Progressive Loading**: Optimized performance for large email volumes
- **Cross-Platform**: Windows, macOS, and Linux support
- **High DPI Support**: 4K and high-resolution display compatibility

## 📁 Project Structure

```
email-attachments-manager/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config/                 # Configuration files
├── models/                 # Database models
├── views/                  # UI components
├── controllers/            # Business logic
├── services/               # External services
├── workers/                # Background processing
├── utils/                  # Utilities and helpers
└── docs/                   # Documentation
```

## 📄 License

This project is licensed under the Copyright (c) 2025 Haider Ali. All Rights Reserved. - see the [LICENSE](LICENSE) file for details.

## ⚠️ Important Notes

- **Environment File**: Never commit `.env` file to version control
- **Template File**: Use `env_template.txt` as a reference for required variables
- **Email Passwords**: All email passwords are encrypted before storage
- **App Passwords**: Use App Passwords for Gmail SMTP authentication
- **Encryption Key**: The `secret.key` file is auto-generated and should never be shared
- **Backup**: Regularly backup your database and configuration files
- **Security**: Keep your `.env` file secure and never share it publicly

## 📚 Additional Documentation

- **[SETUP.md](SETUP.md)** - Detailed setup guide with step-by-step instructions
- **[LICENSE](LICENSE)** - Project license and copyright information

## 🆘 Support

For support, feature requests, or bug reports, please open an issue on GitHub.

---

**Built with ❤️ using PyQt5, Python, and MySQL**

---
