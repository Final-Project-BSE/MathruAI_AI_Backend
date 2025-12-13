# AI Backend System – README

This project contains multiple AI-based modules including:
- Chatbot System
- Pregnancy Daily Recommendation System
- Risk Prediction Model

This document explains **API endpoints, request content, training commands, and how to run the full system**.

---

## Chatbot – Knowledge Base Upload

Use the following API endpoint to upload documents or knowledge base data for the chatbot:

- http://localhost:5000/api/upload


## Daily Recommendation System – Pregnancy Module

To upload PDF documents for the pregnancy daily recommendation system, use:

- http://localhost:5000/pregnancy/upload-pdf


## Risk Prediction Model

### Train the Model

Run the following command to train the risk prediction model:

- python -m risk_predition_model.model.train_model


## Run the Complete System

To start the entire backend system (APIs + models), execute:

- python main.py