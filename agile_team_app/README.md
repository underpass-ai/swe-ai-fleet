# Agile Team Collaboration Platform

A modern web application that enables Human Product Owners to participate in agile software engineering teams alongside AI-powered team members. The platform supports the full agile development lifecycle with real-time collaboration features.

## Features

### 🎯 **Core Functionality**
- **Project Management**: Create and manage software development projects
- **Sprint Planning**: Organize work into time-boxed iterations
- **Task Management**: User stories, bug tracking, and feature development
- **Team Collaboration**: Real-time communication and updates
- **AI Agent Integration**: Automated team members for different roles

### 👥 **Team Roles Supported**
- **Product Owner** (Human): Project vision and requirements
- **Project Manager** (AI): Sprint planning and team coordination
- **Architect** (AI): System design and technical decisions
- **QA Engineer** (AI): Testing strategy and quality assurance
- **DevOps Engineer** (AI): Infrastructure and deployment
- **Backend Developer** (AI): Server-side development
- **Frontend Developer** (AI): User interface development

### 🚀 **Agile Features**
- Sprint planning and execution
- Task boards with drag-and-drop
- Burndown charts and velocity tracking
- Real-time team notifications
- Sprint retrospectives and planning

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM
- **SQLite**: Database (easily upgradeable to PostgreSQL)
- **JWT**: Authentication and authorization
- **WebSockets**: Real-time communication
- **Pydantic**: Data validation

### Frontend
- **React 18**: Modern UI framework
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **React Query**: Server state management
- **React Router**: Client-side routing
- **Vite**: Fast build tool

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd agile_team_app/backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   ```bash
   export SECRET_KEY="your-secret-key-here"
   export DATABASE_URL="sqlite:///./agile_team.db"
   ```

5. **Run the backend:**
   ```bash
   python main.py
   ```

The backend will be available at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd agile_team_app/frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`

## API Documentation

Once the backend is running, you can access the interactive API documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Database Schema

The application uses the following main entities:

- **Users**: Team members (human and AI)
- **Projects**: Software development projects
- **Sprints**: Time-boxed development iterations
- **Tasks**: User stories, bugs, and features
- **Team Members**: Project team composition
- **Comments**: Task discussions and updates

## AI Agent Configuration

AI agents can be configured with specific behaviors and expertise:

```json
{
  "expertise": "backend_development",
  "communication_style": "collaborative",
  "decision_making": "data_driven",
  "specializations": ["API design", "database optimization", "security"]
}
```

## Development

### Project Structure
```
agile_team_app/
├── backend/
│   ├── app/
│   │   ├── routers/          # API endpoints
│   │   ├── models.py         # Database models
│   │   ├── schemas.py        # Pydantic schemas
│   │   └── database.py       # Database configuration
│   ├── main.py               # FastAPI application
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── contexts/        # React contexts
│   │   ├── services/        # API services
│   │   └── App.tsx          # Main application
│   ├── package.json         # Node.js dependencies
│   └── vite.config.ts       # Vite configuration
└── README.md
```

### Adding New Features

1. **Backend**: Add new models, schemas, and API endpoints
2. **Frontend**: Create new components and integrate with API
3. **Database**: Run migrations for schema changes
4. **Testing**: Add unit and integration tests

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Deployment

### Production Considerations
- Use PostgreSQL instead of SQLite
- Set up proper environment variables
- Configure CORS for production domains
- Set up SSL/TLS certificates
- Use production-grade WSGI server (Gunicorn)
- Set up monitoring and logging

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support:
- Create an issue in the repository
- Check the API documentation
- Review the code examples

## Roadmap

- [ ] Advanced AI agent behaviors
- [ ] Integration with external tools (Jira, GitHub)
- [ ] Mobile application
- [ ] Advanced analytics and reporting
- [ ] Multi-tenant support
- [ ] API rate limiting and caching
- [ ] Advanced security features