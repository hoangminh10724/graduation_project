FROM python:3.11-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 && \
    pip install --no-cache-dir transformers==4.49.0 soundfile==0.13.1 && \
    python -c "import soundfile, faster_whisper; from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC"
COPY app app
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
