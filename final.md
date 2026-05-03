@workspace

We are finalizing our project for submission. The grading rubric strictly requires the `README.md` to include three specific things. Please completely rewrite the `README.md` to include the following sections, ensuring the tone is professional and acts as a Senior Engineer's system documentation.

1. **Architecture Diagram:** Please embed the existing architecture diagram image into the document using standard Markdown image syntax. The file is located in the root directory and is named `Incident management system architecture diagram.png`. Make sure this is featured prominently in the Architecture overview section.

2. **Setup Instructions:** Provide clear, step-by-step instructions on how to start the system using our `compose.yaml` file. Include the exact terminal commands (e.g., `docker compose up -d --build`) and a table of the exposed ports (Frontend on 5173, Backend on 8000, etc.) so the reviewer knows where to look.

3. **Backpressure Handling Strategy:** Create a dedicated heading for this. Write 2-3 highly technical paragraphs explaining how our system survives 10,000 signals/sec bursts. Explicitly detail how we use the in-memory Token Bucket for admission control (rejecting excess spikes) and NATS as an asynchronous "shock absorber" to decouple the API ingestion speed from the slower database write speeds.
