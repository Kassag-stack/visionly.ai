import React from "react";
import { json, type LoaderFunctionArgs, type ActionFunctionArgs } from "@remix-run/node";
import { useLoaderData, useActionData, Form } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  Button,
  Text,
  BlockStack,
  TextField,
  Select,
  DataTable,
  Badge,
} from "@shopify/polaris";
import { authenticate } from "../shopify.server";
import axios from "axios";

// Configuration for backend services via environment variables
const BACKEND_CONFIG = {
  finance: {
    url: process.env.FINANCE_API_URL || "",
    description: "Financial data and currency analysis",
  },
  news: {
    url: process.env.NEWS_API_URL || "",
    description: "News sentiment analysis and market insights",
  },
  trends: {
    url: process.env.TRENDS_API_URL || "",
    description: "Google Trends and search analytics",
  },
  meta: {
    url: process.env.META_API_URL || "",
    description: "Meta/Facebook social media analytics",
  },
  tiktok: {
    url: process.env.TIKTOK_API_URL || "",
    description: "TikTok engagement and trend analysis",
  },
  weather: {
    url: process.env.WEATHER_API_URL || "",
    description: "Weather data and forecasting",
  },
} as const;

export const loader = async ({ request }: LoaderFunctionArgs) => {
  await authenticate.admin(request);
  
  return json({
    backendServices: BACKEND_CONFIG,
  });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  await authenticate.admin(request);
  const formData = await request.formData();
  const service = formData.get("service") as string;
  const query = formData.get("query") as string;
  
  try {
    const serviceConfig = BACKEND_CONFIG[service as keyof typeof BACKEND_CONFIG];
    if (!serviceConfig) {
      return json({ error: "Invalid service selected" }, { status: 400 });
    }

    // Make API call to backend service
    const response = await axios.post(serviceConfig.url, {
      query: query,
      timestamp: new Date().toISOString(),
    });

    return json({
      success: true,
      data: response.data,
      service: service,
    });
  } catch (error) {
    console.error("Backend API error:", error);
    return json({ 
      error: "Failed to connect to backend service",
      details: error instanceof Error ? error.message : "Unknown error"
    }, { status: 500 });
  }
};

export default function BackendAPI() {
  const { backendServices } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();

  const serviceOptions = Object.entries(backendServices).map(([key, config]) => ({
    label: `${key.charAt(0).toUpperCase() + key.slice(1)} API`,
    value: key,
  }));

  const rows = actionData?.data ? [
    ["Service", actionData.service],
    ["Status", actionData.success ? "Success" : "Error"],
    ["Response", JSON.stringify(actionData.data, null, 2)],
  ] : [];

  return (
    <Page title="Backend API Integration">
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="500">
              <Text as="h2" variant="headingMd">
                Connect to Visionly AI Backend Services
              </Text>
              <Text as="p" variant="bodyMd">
                Test and integrate with your backend services. Enter a query and select a service to make API calls.
              </Text>
              
              <Form method="post">
                <BlockStack gap="400">
                  <Select
                    label="Backend Service"
                    options={serviceOptions}
                    name="service"
                    required
                  />
                  <TextField
                    label="Query"
                    name="query"
                    placeholder="Enter your query here..."
                    required
                    multiline={3}
                  />
                  <Button submit primary>
                    Call Backend Service
                  </Button>
                </BlockStack>
              </Form>

              {actionData?.error && (
                <Card>
                  <BlockStack gap="200">
                    <Text as="h3" variant="headingMd" tone="critical">
                      Error
                    </Text>
                    <Text as="p" variant="bodyMd" tone="critical">
                      {actionData.error}
                    </Text>
                    {actionData.details && (
                      <Text as="p" variant="bodyMd" tone="subdued">
                        Details: {actionData.details}
                      </Text>
                    )}
                  </BlockStack>
                </Card>
              )}

              {actionData?.success && (
                <Card>
                  <BlockStack gap="200">
                    <Text as="h3" variant="headingMd">
                      Response
                    </Text>
                    <DataTable
                      columnContentTypes={["text", "text"]}
                      headings={["Field", "Value"]}
                      rows={rows}
                    />
                  </BlockStack>
                </Card>
              )}
            </BlockStack>
          </Card>
        </Layout.Section>

        <Layout.Section variant="oneThird">
          <BlockStack gap="500">
            <Card>
              <BlockStack gap="200">
                <Text as="h3" variant="headingMd">
                  Available Services
                </Text>
                {Object.entries(backendServices).map(([key, config]) => (
                  <div key={key}>
                    <Text as="h4" variant="headingSm">
                      {key.charAt(0).toUpperCase() + key.slice(1)} API
                    </Text>
                    <Text as="p" variant="bodyMd" tone="subdued">
                      {config.description}
                    </Text>
                    <Badge tone="info">{config.url || "URL not configured"}</Badge>
                  </div>
                ))}
              </BlockStack>
            </Card>
          </BlockStack>
        </Layout.Section>
      </Layout>
    </Page>
  );
} 