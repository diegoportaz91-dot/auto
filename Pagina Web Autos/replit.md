# Overview

AutoMarket Argentina is a vehicle marketplace web application built with Flask that allows users to browse, view, and contact sellers about vehicles for sale. The platform features a public-facing marketplace for potential buyers and an administrative interface for managing vehicle listings. The system focuses on the Argentine market with pricing in Argentine pesos and WhatsApp integration for direct communication between buyers and sellers.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap 5 for responsive design
- **UI Components**: Custom CSS with Font Awesome icons, carousel image galleries, and responsive cards
- **Client-side**: Vanilla JavaScript for interactive features like offer modals, smooth scrolling, and lazy loading
- **Styling**: Bootstrap 5 framework with custom CSS overrides for branding

## Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Database**: SQLite by default, configurable via environment variables for production databases
- **Session Management**: Flask sessions with configurable secret key
- **File Handling**: Image upload functionality with size limits (16MB) and allowed file type validation
- **Security**: Werkzeug password hashing for admin authentication, proxy fix middleware for deployment

## Data Model Design
- **Vehicle Entity**: Core model with comprehensive attributes (title, description, price, specifications, images stored as JSON)
- **Admin Entity**: Simple admin user model with username and hashed password
- **Analytics Models**: Click tracking and view tracking for business intelligence
- **Relationships**: One-to-many relationships between vehicles and their analytics data

## Authentication System
- **Admin-only Authentication**: Simple session-based authentication for administrative functions
- **No User Registration**: Public marketplace requires no user accounts for browsing
- **Default Credentials**: Environment-configurable admin credentials with fallback defaults

## File Management
- **Image Storage**: Local filesystem storage in static/uploads directory
- **Image Processing**: Client-side validation for file types (PNG, JPG, JPEG, GIF, WEBP)
- **Fallback Images**: Placeholder images for listings without photos

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web application framework
- **SQLAlchemy**: Database ORM and connection management
- **Werkzeug**: Security utilities and WSGI utilities

## Frontend Dependencies
- **Bootstrap 5**: CSS framework via CDN
- **Font Awesome**: Icon library via CDN
- **jQuery**: Not explicitly used, relying on vanilla JavaScript

## Communication Services
- **WhatsApp Integration**: Direct URL generation for WhatsApp messaging with pre-filled contact messages
- **No Email Service**: Currently no email notifications or contact forms

## Database Support
- **SQLite**: Default development database
- **PostgreSQL Compatible**: Configurable for production deployment via DATABASE_URL environment variable
- **Connection Pooling**: Configured for production with pool recycling and pre-ping health checks

## Deployment Configuration
- **Environment Variables**: Support for SESSION_SECRET, DATABASE_URL, and ADMIN_PASSWORD configuration
- **ProxyFix Middleware**: Configured for deployment behind reverse proxies
- **Debug Mode**: Configurable debug mode with default enabled for development