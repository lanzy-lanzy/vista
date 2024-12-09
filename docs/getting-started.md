# Getting Started with Vista v1

This guide will help you set up and run Vista v1 on your system.

## Prerequisites

Before installing Vista v1, ensure you have the following prerequisites:

- Python 3.8 or higher
- pip package manager
- Git (for version control)
- Sufficient storage space for video processing
- CUDA-capable GPU (recommended for optimal performance)

## Installation

1. Clone the Repository
```bash
git clone https://github.com/yourusername/vistav1.git
cd vistav1
```

2. Create a Virtual Environment (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Dependencies
```bash
pip install -r requirements.txt
```

4. Configure Environment Variables
Create a `.env` file in the project root:
```env
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///db.sqlite3
```

5. Initialize Database
```bash
python manage.py migrate
```

6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

## First Run

1. Start the Development Server
```bash
python manage.py runserver
```

2. Access the Application
- Open your browser and navigate to `http://localhost:8000`
- Admin interface is available at `http://localhost:8000/admin`

## Basic Usage

### Uploading a Video for Analysis

1. Navigate to the upload page
2. Select a video file from your computer
3. Click "Upload and Analyze"
4. Monitor the analysis progress
5. View results in the dashboard

### Live Camera Feed

1. Ensure your camera is connected and recognized
2. Navigate to the live feed section
3. Select your camera from the dropdown
4. Start the live analysis

## Next Steps

- Read the [Configuration Guide](./configuration.md) for customizing settings
- Check out the [API Reference](./api-reference.md) for integration
- Visit [Troubleshooting](./troubleshooting.md) if you encounter issues
