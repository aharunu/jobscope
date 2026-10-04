FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Resolve only the runtime dependencies declared by the project; source edits
# do not invalidate this layer. Constraints pin the tested Linux runtime.
COPY pyproject.toml ./
COPY backend/requirements.lock ./requirements.lock
RUN python -c "import tomllib, subprocess; subprocess.check_call(['pip', 'install', '--no-cache-dir', '-c', 'requirements.lock', *tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']])"

RUN useradd --create-home --uid 1000 jobscope
COPY --chown=jobscope:jobscope backend ./backend
COPY --chown=jobscope:jobscope data ./data
COPY --chown=jobscope:jobscope alembic.ini ./
COPY --chown=jobscope:jobscope scripts/docker_backend_start.py ./scripts/docker_backend_start.py

USER jobscope
EXPOSE 8000
ENTRYPOINT ["python", "scripts/docker_backend_start.py"]
CMD ["uvicorn", "backend.interfaces.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "backend"]
