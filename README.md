⭐ Recommended Development Setup
## Development Setup
Follow the steps below to configure the local development environment for the Fitness-Manager project.

### 1. Install Python
Ensure Python 3.10 or newer is installed on your system.
Verify the installation:
python --version

2. Create a Virtual 
From the project root directory, create a virtual environment:
python -m venv venv

Activate the environment:
Windows (PowerShell):
.\venv\Scripts\Activate

macOS/Linux:
source venv/bin/activate

3. Install Project Dependencies
Install the required packages using:
pip install -r requirements.txt

4. Configure the Database
Ensure MongoDB is running locally or via Docker before starting the application.
Example (Docker):
docker compose up -d

5. Apply Migrations
python manage.py migrate

6. Run the Development Server
python manage.py runserver

The application should now be available at:
http://127.0.0.1:8000/

