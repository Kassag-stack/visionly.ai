(NOTICE: This is a copy of the original repositary since my teammate who is the owner of the orginal repositary)
# fy- Shopify Analytics Platform

# https://youtu.be/AFF7qzg_0t8

A comprehensive analytics platform that integrates with Shopify to provide intelligent insights through multiple data sources and AI-powered analysis.

## Features

- **Multi-Source Analytics**: Integrates TikTok, Meta, News, Finance, and Google Trends data
- **AI-Powered Insights**: Advanced statistical analysis and recommendations
- **Shopify Integration**: Direct connection to Shopify store data
- **Real-time Processing**: Asynchronous job processing for large datasets
- **Modern API**: FastAPI-based backend with RESTful endpoints
- **Data Visualization**: Automated chart generation and visual analytics

## System Overview

The following diagram illustrates how the Visionly AI platform integrates with Shopify and processes data through multiple external APIs:

![System Architecture](https://github.com/AbdulAaqib/visionly.ai/blob/7a1444577c36b50cb42c0b829f367a05b576a14b/extra/SCR-20250622-liho.png)


### Data Flow

1. **User Interaction**: Business owners interact with the system through the Shopify interface
2. **Shopify Integration**: The platform connects directly to Shopify stores to access product, sales, and customer data
3. **Fy. Platform**: Acts as the central hub, featuring:
   - **Chatbot Interface**: User-friendly interface for queries and interactions
   - **LLM (Large Language Model)**: Processes natural language queries and generates insights
   - **API Layer**: Manages communication with external data sources
4. **Custom Aggregator**: Combines data from multiple sources for comprehensive analysis
5. **External Data Sources**: 
   - Google Trends for search and market trends
   - TikTok for social media engagement and viral content analysis
   - Meta (Facebook/Instagram) for social media insights
   - Financial Markets for economic indicators and currency data
   - Weather data for seasonal analysis
   - News APIs for market sentiment and industry updates

## Architecture

### Backend Services

The platform consists of multiple specialized API services:

- **TikTok API**: Engagement metrics, hashtag analysis, sentiment tracking
- **Meta API**: Facebook/Instagram analytics and social media insights
- **News API**: Market sentiment analysis and news trend monitoring
- **Finance API**: Currency analysis and financial market data
- **Google Trends API**: Search trend analysis and market research
- **Combined Insights**: AI-powered analysis merging all data sources

### Frontend Components

- **Shopify App**: Remix-based application with Shopify integration
- **API Endpoints**: FastAPI service for processing and job management
- **Database**: Prisma-based data storage and session management

## Project Structure

```
visionly.ai/
├── app/                          # Shopify Remix app
│   ├── routes/
│   │   ├── _index.tsx           # Main dashboard
│   │   └── api.backend.ts       # Backend API integration
│   ├── shopify.server.ts        # Shopify configuration
│   └── db.server.ts             # Database setup
├── backend_api_backup/          # Backend services
│   ├── combined_insight/        # AI analysis and insights
│   ├── tiktok_api/             # TikTok data processing
│   ├── meta_api/               # Meta/Facebook analytics
│   ├── news_api/               # News sentiment analysis
│   ├── finance_api/            # Financial data analysis
│   ├── google_trends/          # Google Trends integration
│   └── frontend_api/           # API endpoints and job processing
├── backend-api/                # Alternative frontend API
└── prisma/                     # Database schema
```

## Setup

### Prerequisites

- Python 3.8+
- Node.js 18+
- Shopify Partner account
- API keys for external services (TikTok, Meta, News, Finance APIs)

### Backend Setup

1. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure environment variables**:
Create a `.env` file with your API keys:
```env
# External API Keys
TIKTOK_API_KEY=your_tiktok_api_key
META_API_KEY=your_meta_api_key
NEWS_API_KEY=your_news_api_key
FINANCE_API_KEY=your_finance_api_key
GOOGLE_TRENDS_API_KEY=your_google_trends_key

# Database
DATABASE_URL=your_database_url
```

3. **Start the backend API server**:
```bash
cd backend_api_backup/frontend_api
python api_endpoint.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Install Node.js dependencies**:
```bash
npm install
```

2. **Configure Shopify app**:
```bash
cp .env.example .env
```

Update `.env` with your Shopify credentials:
```env
SHOPIFY_API_KEY=your_shopify_api_key
SHOPIFY_API_SECRET=your_shopify_api_secret
SHOPIFY_APP_URL=your_app_url
SCOPES=write_products,read_products,write_orders,read_orders
DATABASE_URL=file:./dev.db
```

3. **Set up database**:
```bash
npx prisma db push
```

4. **Start the development server**:
```bash
npm run dev
```

## API Usage

### Submit Analysis Job

**POST** `/api/chat/completions`

```json
{
  "messages": [
    {
      "role": "user",
      "content": "{\"Products\": [...], \"Collections\": [...], ...}"
    }
  ]
}
```

**Response**:
```json
{
  "status": "success",
  "job_id": "uuid-string",
  "message": "Job submitted successfully"
}
```

### Check Job Status

**GET** `/api/chat/status/{job_id}`

**Response**:
```json
{
  "status": "completed",
  "progress": 100,
  "result": {
    "insights": {...},
    "visualization_files": {...},
    "detailed_analysis": {...}
  }
}
```

## Data Sources

### Shopify Data
- Products and variants
- Collections and categories
- Sales and order data
- Customer analytics

### External APIs
- **TikTok**: Engagement metrics, hashtag trends, viral content analysis
- **Meta**: Facebook/Instagram insights, ad performance, social engagement
- **News**: Market sentiment, industry news, competitor analysis
- **Finance**: Currency rates, market data, economic indicators
- **Google Trends**: Search volume, trending topics, market interest

## Analysis Features

### Statistical Analysis
- Engagement forecasting
- Sentiment analysis
- Trend correlation
- Performance metrics

### Visualizations
- Engagement scatter plots
- Hashtag analysis charts
- Sentiment distribution graphs
- Time series forecasts
- Word clouds and market insights

### AI Insights
- Market opportunity identification
- Growth recommendations
- Competitive analysis
- Trend predictions

## Testing

### Backend API Testing

Use the provided test script:
```bash
cd backend_api_backup/frontend_api
python test.py
```

### Manual Testing

1. Start the backend server
2. Submit a test job with sample Shopify data
3. Monitor job progress and retrieve results
4. Verify visualization files are generated

## Deployment

### Backend Deployment

1. **Prepare production environment**:
```bash
pip install -r requirements.txt
```

2. **Configure production settings**:
- Update CORS origins for production domains
- Set proper database connections
- Configure logging and monitoring

3. **Deploy with production WSGI server**:
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend_api_backup.frontend_api.api_endpoint:app
```

### Frontend Deployment

1. **Build the Shopify app**:
```bash
npm run build
```

2. **Deploy to hosting platform** (Vercel, Railway, etc.)

3. **Update Shopify app configuration** with production URLs

## Troubleshooting

### Common Issues

- **CORS errors**: Update `allow_origins` in `api_endpoint.py`
- **Job timeouts**: Check external API rate limits and connectivity
- **Missing visualizations**: Verify file paths and permissions
- **Database errors**: Check Prisma configuration and migrations

### Debugging

- Check server logs for detailed error messages
- Use the test script to verify API connectivity
- Monitor job status for processing errors
- Verify external API credentials and quotas

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with the provided test scripts
5. Submit a pull request

## License

This project is part of the Visionly AI ecosystem. All rights reserved.
