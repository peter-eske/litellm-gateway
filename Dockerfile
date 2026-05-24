FROM litellm/litellm:main-stable

COPY litellm-config.yaml /app/config.yaml

EXPOSE 4000

CMD ["--port", "4000", "--config", "/app/config.yaml"]
