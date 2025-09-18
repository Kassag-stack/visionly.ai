import React from "react";
import { json, type LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  Button,
  Text,
  BlockStack,
  InlineStack,
  Badge,
} from "@shopify/polaris";
import { authenticate } from "../shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin } = await authenticate.admin(request);

  const response = await admin.graphql(
    `#graphql
      query {
        shop {
          name
          plan {
            displayName
            partnerDevelopment
            shopifyPlus
          }
        }
      }`,
  );

  const responseJson = await response.json();

  return json({
    shop: responseJson.data.shop,
  });
};

export default function Index() {
  const { shop } = useLoaderData<typeof loader>();

  return (
    <Page>
      <BlockStack gap="500">
        <Layout>
          <Layout.Section>
            <Card>
              <BlockStack gap="500">
                <BlockStack gap="200">
                  <Text as="h2" variant="headingMd">
                    Welcome to Visionly AI Shopify App
                  </Text>
                  <Text as="p" variant="bodyMd">
                    This app integrates with your Visionly AI backend services to provide
                    intelligent insights for your Shopify store.
                  </Text>
                </BlockStack>
                <InlineStack gap="300">
                  <Button primary>Connect to Backend</Button>
                  <Button>View Analytics</Button>
                </InlineStack>
              </BlockStack>
            </Card>
          </Layout.Section>
          <Layout.Section variant="oneThird">
            <BlockStack gap="500">
              <Card>
                <BlockStack gap="200">
                  <Text as="h3" variant="headingMd">
                    Store Info
                  </Text>
                  <Text as="p" variant="bodyMd">
                    Store: {shop.name}
                  </Text>
                  <Text as="p" variant="bodyMd">
                    Plan: {shop.plan.displayName}
                  </Text>
                  {shop.plan.shopifyPlus && (
                    <Badge tone="success">Shopify Plus</Badge>
                  )}
                </BlockStack>
              </Card>
            </BlockStack>
          </Layout.Section>
        </Layout>
      </BlockStack>
    </Page>
  );
} 