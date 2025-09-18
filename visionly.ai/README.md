# Visionly AI Shopify App

A modern Shopify app that integrates with Visionly AI backend services to provide intelligent insights for your Shopify store.

## Features

- **Backend Service Integration**: Connect to all Visionly AI backend services
- **Modern UI**: Built with Shopify Polaris design system
- **Real-time Analytics**: Get insights from multiple data sources
- **Secure Authentication**: Shopify OAuth integration
- **Database Storage**: Prisma-based session and API call logging

## Backend Services

The app integrates with the following Visionly AI backend services:

- **Finance API**: Financial data and currency analysis
- **News API**: News sentiment analysis and market insights  
- **Trends API**: Google Trends and search analytics
- **Meta API**: Meta/Facebook social media analytics
- **TikTok API**: TikTok engagement and trend analysis
- **Weather API**: Weather data and forecasting

## Setup

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Shopify Partner account
- Visionly AI backend services running

### Installation

1. Clone the repository and navigate to the app directory:
```bash
cd frontend/visionly-shopify-app
```

2. Install dependencies:
```bash
npm install
```

3. Set up environment variables:

- Create a local `.env` file and populate required variables securely. Do not commit `.env`.
- Required variables include Shopify credentials, database URL, and backend service URLs. Refer to code comments for names.

4. Example variable names (values intentionally omitted):

- SHOPIFY_API_KEY
- SHOPIFY_API_SECRET
- SHOPIFY_APP_URL
- SCOPES
- DATABASE_URL
- FINANCE_API_URL
- NEWS_API_URL
- TRENDS_API_URL
- META_API_URL
- TIKTOK_API_URL
- WEATHER_API_URL

5. Set up the database:
```bash
npx prisma db push
```

6. Start the development server:
```bash
npm run dev
```

## Usage

1. **Install the app** in your Shopify store through the Shopify Partner dashboard
2. **Navigate to the app** in your Shopify admin
3. **Go to the Backend API page** to test connections to your backend services
4. **Enter queries** and select services to make API calls
5. **View responses** and integrate insights into your store operations

## Development

### Project Structure

```
app/
├── routes/           # Remix routes
│   ├── _index.tsx   # Main dashboard
│   └── api.backend.ts # Backend API integration
├── shopify.server.ts # Shopify app configuration
├── db.server.ts     # Database configuration
└── root.tsx         # Root component
prisma/
└── schema.prisma    # Database schema
```

### Adding New Backend Services

1. Update the `BACKEND_CONFIG` in `app/routes/api.backend.ts`
2. Add the service URL to your environment variables
3. Test the integration through the app interface

### Customizing the UI

The app uses Shopify Polaris components for consistent design. Modify components in the routes to customize the interface.

## Deployment

1. Build the app:
```bash
npm run build
```

2. Deploy to your hosting platform (Vercel, Netlify, etc.)

3. Update your Shopify app settings with the production URL

## API Integration

The app makes HTTP POST requests to your backend services with the following structure:

```json
{
  "query": "user_input_query",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

Expected response format:
```json
{
  "success": true,
  "data": {
    // Your service-specific data
  }
}
```

## Troubleshooting

- **Authentication errors**: Check your Shopify API credentials
- **Database errors**: Ensure Prisma is properly configured
- **Backend connection errors**: Verify your backend service URLs and CORS settings
- **Build errors**: Check TypeScript compilation and dependency versions

## Support

For issues related to:
- **Shopify App**: Check the Shopify documentation
- **Backend Services**: Contact your Visionly AI backend team
- **General Issues**: Review the logs and error messages

## Security

- Never commit real API keys, secrets, or service URLs.
- Store configuration only in local environment variables.
- Ensure `.env` is in `.gitignore` (already configured).

## License

This project is part of the Visionly AI ecosystem.
