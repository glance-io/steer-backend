![Logo Banner](logo_banner.png)
# Steer

Lightweight backend service for [grammar assistant app](https://steerapp.ai/).
Can serve as an inspiration for LLM token streaming with OpenAI SDK and FastAPI.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

The project requires Python and pip installed on your system. The required Python packages are listed in the `requirements.txt` file.

### Environment
Copy the `.env.example` file to `.env` and fill in the required values.

```bash
cp .env.example .env
```

### Config
To configure the application, especially the LLM prompts, copy the `config.example.yaml` file to `config.yaml` and fill in the required values.

```bash
cp config.example.yaml config.yaml
```

### Installing

1. Clone the repository to your local machine.
2. Navigate to the project directory.
3. Install the required packages using pip:

```bash
pip install -r requirements.txt
```

## Running the Application

To run the application, use the following command:

```bash
uvicorn main:app --reload
```

Or you can run the application with Docker:

```bash
docker-compose up
```
The application will be available at `http://localhost:80` exposed with Nginx.



## Project Structure

The project is structured into several modules and services. For people interested only in LLM integration, the most interesting parst will be:

- [LLM service](app/services/openai_service.py)
- [Rewrite service](app/services/rewrite_service.py)

Endpoint documentation is available at `/docs` when the application is running.
