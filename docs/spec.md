# Spec — eBay E2E Automation Drill (translated from Hebrew)

## 1. Goal of the exercise
1. Implement an E2E scenario against the example commerce site **eBay**: product search, price filtering, add to cart, and total-amount verification.
2. Demonstrate a clean architecture: **Page Object Model, OOP, Data-Driven**.

## 2. Time frame
3–4 net hours for implementation + 20–30 minutes for review/demo.

## 3. General requirements
- Allowed automation tools: **Playwright**
- Allowed languages: **Python**
- Allowed reporting: **Extent Reports, Allure Reports, Report Portal**
- Must use object-oriented development
- Must use the POM model
- **Data-Driven**: test inputs come from an external file (JSON/CSV/YAML)

## 4. Project description
Develop 4 core functions:
- Authentication (login)
- Search function with a price condition
- `addItemsToCart`
- `assertCartTotalNotExceeds`

### 4.1 Search function with price condition
Example signature (TypeScript, Playwright):

```ts
// returns up to N links to items whose price <= maxPrice
async function searchItemsByNameUnderPrice(query: string, maxPrice: number, limit = 5): Promise<string[]>
```

Behavior:
- Perform a search by `query`.
- If a price filter exists on the page, use it (min/max) to narrow the results.
- Use **XPath** to extract the first `limit` (e.g. five) items whose price is ≤ `maxPrice`.
- Special case — fewer than 5 items on the current page:
  - If pagination is available ("Next" button or page navigation), move to the next page and keep collecting items until 5 are reached or pages run out.
  - If pagination is not available, return however many items were found (even if fewer than 5).
- Return: an array of URLs of up to 5 results that meet the price condition.
- If fewer are found, return what is available (even 0 is valid).

Example usage:

```ts
const urls = await searchItemsByNameUnderPrice("shoes", 220, 5);
```

### 4.2 Function that adds items to the cart
Signature:

```ts
async function addItemsToCart(urls: string[]): Promise<void>
```

Behavior:
- Loop over each URL and open the item page.
- If variants must be chosen (size/color/quantity), pick values **randomly** from the available ones.
- Click **"Add to cart"**.
- Return to the search screen/tab.
- Save a **screenshot/log** for each item added.

### 4.3 Function that asserts the cart total
Signature:

```ts
async function assertCartTotalNotExceeds(budgetPerItem: number, itemsCount: number): Promise<void>
```

Behavior:
- Open the cart.
- Read the subtotal / grand total (as shown on the site).
- Compute threshold: `budgetPerItem * itemsCount`.
- Assert that the total does **not** exceed the threshold.
- Save a **screenshot/trace** of the cart page.

### Full scenario example
- Call `searchItemsByNameUnderPrice("shoes", 220, 5)` — receive up to 5 links.
- `addItemsToCart(urls)` — adds them all to the cart.
- `assertCartTotalNotExceeds(220, urls.length)` — asserts cart total ≤ `220 * number of items`.
