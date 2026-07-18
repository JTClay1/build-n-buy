# Build n' Buy

Build n' Buy is a full-stack personal finance planning app designed to help users plan purchases before they buy them. Instead of encouraging impulse spending, the app helps users create savings goals, track progress, compare retailer prices, monitor price changes, and use an AI-powered advisor to make smarter buying decisions.

The core idea is simple: if a user wants something, Build n' Buy helps them build a realistic plan to afford it.

---

## Live Deployment

Frontend: https://build-n-buy.vercel.app

Backend API: https://build-n-buy.onrender.com

Backend Health Check: https://build-n-buy.onrender.com/api/health

---

## Project Summary

Build n' Buy combines goal-based saving, budgeting, price tracking, notifications, and AI guidance into one planning workspace.

Users can:

- Create and manage savings goals
- Track deposits and withdrawals
- Compare saved retailer URLs for a goal
- Refresh live prices from retailer product pages
- Receive notifications when price-related events occur
- Add income and expense information
- Ask an AI advisor whether a purchase makes sense
- Save useful advisor responses for later review
- Review saved advisor responses with pagination
- Use the app in light or dark mode

This project was built as a full-stack capstone using a Flask backend, React frontend, PostgreSQL production database, JWT authentication, live scraping through ScraperAPI, and OpenAI-powered advisor responses.

---

## Why This App Exists

Most wishlist and shopping apps focus on buying faster.

Build n' Buy focuses on buying smarter.

The app is built around the idea that a purchase decision should consider:

- Current savings
- Monthly budget
- Goal priority
- Remaining cost
- Time until target date
- Price movement
- Cheaper alternatives
- Whether waiting makes more sense than buying now

Build n' Buy gives users a central place to organize that decision before spending money.

---

## Tech Stack

### Frontend

- React
- Vite
- React Router
- JavaScript
- CSS
- Vercel deployment

### Backend

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-Bcrypt
- Flask-JWT-Extended
- Flask-CORS
- Gunicorn
- Render deployment

### Database

- SQLite for local development
- PostgreSQL for production on Render

### External APIs

- OpenAI API for Smart Advisor responses
- ScraperAPI for retailer product-page scraping

### Testing

- Unit tests added for project verification
- Frontend test command depends on the configured package scripts
- Backend tests can be run with pytest if backend tests are present

---

## Main Features

## 1. User Authentication

Users can sign up, log in, and access protected pages using JWT authentication.

Authentication features include:

- User signup
- User login
- Protected frontend routes
- Authenticated API requests
- Current user profile lookup
- JWT-based session handling
- Session timeout behavior

Primary auth routes:

- POST /api/auth/signup
- POST /api/auth/login
- GET /api/auth/me
- PATCH /api/auth/profile
- PATCH /api/auth/password

---

## 2. Dashboard

The dashboard gives users a quick overview of their financial planning activity.

It includes:

- Active goals
- Saved amount
- Remaining amount
- Goal progress
- Budget snapshot
- Goal cards
- Notifications
- Smart Advisor widget access

The dashboard acts as the main hub after login.

---

## 3. Savings Goals

Users can create goals for items they want to buy.

Each goal can track:

- Item name
- Retailer/source
- Target amount
- Saved amount
- Target date or timeline
- Monthly target
- Goal status
- Contributions
- Retailer prices
- Advisor responses

Goal features include:

- Create a new goal
- View goal details
- Edit goal information
- Delete a goal
- Track savings progress
- View remaining balance
- View progress toward the target amount
- Mark or manage goal status

Primary goal routes:

- GET /api/goals
- POST /api/goals
- GET /api/goals/:id
- PATCH /api/goals/:id
- DELETE /api/goals/:id

---

## 4. Contributions and Withdrawals

Users can add money toward a goal or remove money when plans change.

Contribution features include:

- Add savings deposits
- Add withdrawals
- Track notes for entries
- Update saved goal balance
- View contribution history
- Delete individual contribution records

Contribution routes:

- POST /api/goals/:goal_id/contributions
- DELETE /api/contributions/:contribution_id

---

## 5. Monthly Timeline and Progress Tracking

Build n' Buy helps users understand how realistic a purchase goal is over time.

Goal detail pages include:

- Current saved amount
- Remaining amount
- Monthly target
- Progress percentage
- Time-based planning information
- Visual progress indicators

This helps users answer questions like:

- How much do I still need?
- How much should I save per month?
- Am I on pace?
- Is this goal realistic with my current budget?

---

## 6. Budget and Profile Context

Users can add personal budget context so the app and advisor can make better recommendations.

Budget-related data can include:

- Monthly income
- Recurring expenses
- Budget categories
- Available money after expenses
- Available money after savings goals

Budget features include:

- Add budget items
- Edit budget items
- Delete budget items
- View budget summary
- Use budget context in Smart Advisor responses

Budget routes:

- GET /api/budget-items
- POST /api/budget-items
- PATCH /api/budget-items/:id
- DELETE /api/budget-items/:id

---

## 7. Smart Buy Advisor

The Smart Buy Advisor is an AI-powered planning assistant built into the app.

Users can ask questions like:

- Which goal should I prioritize?
- Can I afford my current active goals?
- Should I buy now or wait?
- What cheaper alternatives should I consider?
- How should I adjust my budget for this purchase?
- Is this goal realistic based on my current finances?

Advisor responses can use:

- Goal data
- Saved amount
- Remaining amount
- Budget context
- Retailer price information
- Price comparison information
- User-provided questions

Advisor features include:

- Full-page advisor workspace
- Dashboard advisor widget
- Goal-specific advisor prompts
- AI-generated recommendations
- Action items
- Advisor notes
- Saved responses
- Delete saved responses
- Paginated saved advisor responses

Advisor routes:

- POST /api/advisor
- GET /api/advisor/history
- POST /api/advisor/save
- GET /api/advisor/snapshot
- DELETE /api/advisor/responses/:id

---

## 8. Saved Advisor Responses

Users can save useful AI responses and review them later.

Saved responses include:

- Original user question
- Context type
- AI-generated summary
- Recommendations
- Action items
- Advisor note
- Created timestamp

Saved responses are paginated at 5 responses per page to keep the Advisor page readable as history grows.

---

## 9. Retailer Price Tracking

Users can save retailer product URLs for a specific goal and compare prices.

Price tracking supports:

- Add retailer/product URL
- Save manual price information
- Refresh a single retailer price
- Refresh all saved retailer prices for a goal
- Compare retailer prices
- Show lowest saved retailer price
- Display last checked timestamps
- Update price summaries

Price routes:

- GET /api/goals/:goal_id/prices
- POST /api/goals/:goal_id/prices
- PATCH /api/prices/:price_id
- DELETE /api/prices/:price_id
- PATCH /api/prices/:price_id/refresh
- POST /api/goals/:goal_id/prices/refresh
- POST /api/prices/daily-check

---

## 10. Live Price Scraping

Build n' Buy uses ScraperAPI to fetch retailer product pages and extract live product prices.

The live scraper can:

- Validate saved retailer URLs
- Reject invalid shopping URLs like homepages, carts, login pages, or checkout pages
- Fetch product page HTML through ScraperAPI
- Parse product prices from structured data, metadata, and page content
- Update saved retailer prices
- Track when a price was last checked
- Support retailer-specific extraction strategies where possible

The scraper is designed to support real-world product URLs from major retailers, but scraping can still depend on the retailer's page structure, bot protection, and response format.

---

## 11. Notifications

The app includes a notification system to keep users informed about important events.

Notification features include:

- Notification bell
- Unread notification count
- Mark individual notifications as read
- Mark all notifications as read
- Demo notification route
- Price-related notification support

Notification routes:

- GET /api/notifications
- POST /api/notifications/demo
- PATCH /api/notifications/:id/read
- PATCH /api/notifications/read-all

---

## 12. Dark Mode

Build n' Buy includes a dark mode experience for the frontend UI.

Dark mode supports:

- App-wide theme switching
- Dark dashboard styling
- Dark goal detail styling
- Dark advisor page styling
- Dark profile/budget styling
- Theme-aware cards and panels

---

## 13. Deployment

Build n' Buy is deployed with:

- Vercel for the React frontend
- Render for the Flask backend
- Render PostgreSQL for production data

The production frontend communicates with the production backend through the VITE_API_BASE_URL environment variable.

---

## Project Structure

The project is organized into a client folder and a server folder.

```txt
build-n-buy/
├── client/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── vercel.json
│
├── server/
│   ├── migrations/
│   ├── routes/
│   ├── services/
│   ├── app.py
│   ├── config.py
│   ├── extensions.py
│   ├── models.py
│   ├── requirements.txt
│   └── seed.py
│
└── README.md
```

---

## Data Models

## User

Represents an authenticated user.

A user can have:

- Goals
- Advisor responses
- Notifications
- Budget items

Common fields include:

- id
- username
- email
- password_hash
- display_name
- monthly_budget

---

## Goal

Represents a savings goal or planned purchase.

A goal can have:

- Contributions
- Retailer prices
- Advisor responses
- Notifications

Common fields include:

- id
- user_id
- item_name
- retailer/source
- target_amount
- saved_amount
- months_to_goal
- target_date
- status
- created_at

---

## Contribution

Represents a deposit or withdrawal connected to a goal.

Common fields include:

- id
- goal_id
- amount
- entry_type
- note
- contribution_date

---

## RetailerPrice

Represents a saved retailer listing for a goal.

Common fields include:

- id
- goal_id
- retailer_name
- product_url
- current_price
- previous_price
- last_checked_at
- created_at

---

## SmartAdvisorResponse

Represents a saved AI advisor response.

Common fields include:

- id
- user_id
- goal_id
- context_type
- user_message
- response_json
- created_at

---

## Notification

Represents an in-app notification.

Common fields include:

- id
- user_id
- goal_id
- message
- notification_type
- is_read
- created_at

---

## BudgetItem

Represents an income or expense item used for budget planning.

Common fields include:

- id
- user_id
- name
- amount
- category/type
- created_at

---

## Local Setup

## Prerequisites

Make sure you have the following installed:

- Node.js
- npm
- Python 3
- Pipenv
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/JTClay1/build-n-buy.git
cd build-n-buy
```

---

## 2. Backend Setup

Move into the server folder:

```bash
cd server
```

Install Python dependencies:

```bash
pipenv install
```

Enter the virtual environment:

```bash
pipenv shell
```

Set up the database:

```bash
flask db upgrade
```

Optional: seed the database if a seed file is available:

```bash
python seed.py
```

Run the Flask server:

```bash
python app.py
```

The backend should run at:

```txt
http://localhost:5555
```

---

## 3. Frontend Setup

In a separate terminal, move into the client folder:

```bash
cd client
```

Install frontend dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend should run at:

```txt
http://localhost:5173
```

---

## Environment Variables

## Backend Environment Variables

Create a `.env` file in the `server` folder for local development if needed.

Example:

```env
JWT_SECRET_KEY=your-local-jwt-secret
OPENAI_API_KEY=your-openai-api-key
OPENAI_ADVISOR_MODEL=your-openai-model
SCRAPERAPI_KEY=your-scraperapi-key
PRICE_SCRAPE_RENDER=false
PRICE_SCRAPE_COUNTRY=us
FRONTEND_URL=http://localhost:5173
```

Production on Render also uses:

```env
DATABASE_URL=your-render-postgres-url
FRONTEND_URL=https://build-n-buy.vercel.app
```

Important:

- Do not commit `.env` files.
- Do not commit API keys.
- Use Render environment variables for production backend secrets.

---

## Frontend Environment Variables

Create a `.env` file in the `client` folder for local frontend configuration if needed.

Local example:

```env
VITE_API_BASE_URL=http://localhost:5555/api
```

Production Vercel example:

```env
VITE_API_BASE_URL=https://build-n-buy.onrender.com/api
```

Important:

- Vite only exposes environment variables that start with `VITE_`.
- After changing Vercel environment variables, redeploy the frontend.

---

## Running Tests

## Frontend Tests

From the client folder:

```bash
cd client
npm test
```

If the project uses a different frontend test script, check `client/package.json` and run the configured test command.

---

## Backend Tests

From the server folder:

```bash
cd server
python -m pytest
```

If using Pipenv:

```bash
cd server
pipenv run pytest
```

---

## Build Checks

## Frontend Build

From the client folder:

```bash
npm run build
```

This verifies that the Vite frontend compiles successfully for production.

---

## Backend Compile Check

From the server folder:

```bash
python -m py_compile app.py
```

If using Pipenv:

```bash
pipenv run python -m py_compile app.py
```

---

## API Reference

## Auth

### POST /api/auth/signup

Creates a new user account.

Example request:

```json
{
  "username": "demo_user",
  "email": "demo@example.com",
  "password": "password123"
}
```

### POST /api/auth/login

Logs in an existing user and returns a token.

Example request:

```json
{
  "email": "demo@example.com",
  "password": "password123"
}
```

### GET /api/auth/me

Returns the currently authenticated user.

Requires authentication.

### PATCH /api/auth/profile

Updates profile information.

Requires authentication.

### PATCH /api/auth/password

Updates the current user's password.

Requires authentication.

---

## Goals

### GET /api/goals

Returns the authenticated user's goals.

Requires authentication.

### POST /api/goals

Creates a new goal.

Requires authentication.

### GET /api/goals/:id

Returns one goal.

Requires authentication.

### PATCH /api/goals/:id

Updates a goal.

Requires authentication.

### DELETE /api/goals/:id

Deletes a goal.

Requires authentication.

---

## Contributions

### POST /api/goals/:goal_id/contributions

Adds a deposit or withdrawal to a goal.

Requires authentication.

### DELETE /api/contributions/:contribution_id

Deletes a contribution record.

Requires authentication.

---

## Dashboard

### GET /api/dashboard

Returns dashboard summary information.

Requires authentication.

---

## Advisor

### POST /api/advisor

Creates a new advisor response.

Requires authentication.

### GET /api/advisor/history

Returns saved advisor response history.

Requires authentication.

### POST /api/advisor/save

Saves an advisor response.

Requires authentication.

### GET /api/advisor/snapshot

Returns advisor page snapshot data.

Requires authentication.

### DELETE /api/advisor/responses/:id

Deletes a saved advisor response.

Requires authentication.

---

## Notifications

### GET /api/notifications

Returns user notifications.

Requires authentication.

### POST /api/notifications/demo

Creates a demo notification.

Requires authentication.

### PATCH /api/notifications/:id/read

Marks one notification as read.

Requires authentication.

### PATCH /api/notifications/read-all

Marks all notifications as read.

Requires authentication.

---

## Budget Items

### GET /api/budget-items

Returns budget items.

Requires authentication.

### POST /api/budget-items

Creates a budget item.

Requires authentication.

### PATCH /api/budget-items/:id

Updates a budget item.

Requires authentication.

### DELETE /api/budget-items/:id

Deletes a budget item.

Requires authentication.

---

## Price Tracking

### GET /api/goals/:goal_id/prices

Returns saved retailer prices for a goal.

Requires authentication.

### POST /api/goals/:goal_id/prices

Adds a retailer price record to a goal.

Requires authentication.

### PATCH /api/prices/:price_id

Updates a retailer price record.

Requires authentication.

### DELETE /api/prices/:price_id

Deletes a retailer price record.

Requires authentication.

### PATCH /api/prices/:price_id/refresh

Refreshes one saved retailer price.

Requires authentication.

### POST /api/goals/:goal_id/prices/refresh

Refreshes all saved retailer prices for a goal.

Requires authentication.

### POST /api/prices/daily-check

Runs a daily price check workflow.

Requires authentication or production-safe access depending on deployment configuration.

---

## Deployment Notes

## Render Backend

Render backend settings:

```txt
Build Command:
pip install -r server/requirements.txt

Start Command:
cd server && gunicorn --timeout 180 app:app
```

The extended Gunicorn timeout gives the live scraper enough time to check multiple retailer URLs.

Important Render environment variables:

```env
DATABASE_URL=your-render-postgres-url
JWT_SECRET_KEY=your-production-jwt-secret
OPENAI_API_KEY=your-openai-api-key
OPENAI_ADVISOR_MODEL=your-openai-model
SCRAPERAPI_KEY=your-scraperapi-key
PRICE_SCRAPE_RENDER=false
PRICE_SCRAPE_COUNTRY=us
FRONTEND_URL=https://build-n-buy.vercel.app
```

---

## Vercel Frontend

Vercel environment variable:

```env
VITE_API_BASE_URL=https://build-n-buy.onrender.com/api
```

Vercel is configured for single-page app routing so direct page refreshes still route to `index.html`.

---

## Production CORS Notes

The backend allows requests from:

- http://localhost:5173
- http://127.0.0.1:5173
- https://build-n-buy.vercel.app

The backend also explicitly supports CORS preflight requests for authenticated API calls using:

- Authorization headers
- Content-Type headers
- GET
- POST
- PATCH
- DELETE
- OPTIONS

This is important because the frontend sends authenticated requests to the Render backend from the Vercel domain.

---

## Known Limitations

Build n' Buy uses live retailer scraping, and retailer pages can change over time.

A scrape may fail if:

- The retailer changes its HTML structure
- The retailer blocks automated requests
- The product URL is invalid
- The URL points to a homepage, cart, login page, or search page instead of a product page
- The retailer requires JavaScript-rendered content that is not available in the returned HTML
- The external scraping provider times out or returns a blocked response

The app handles these cases by showing user-facing error messages instead of crashing.

---

## Future Improvements

Potential future improvements include:

- Email notifications for major price drops
- More advanced price history charts
- More retailer-specific scraping strategies
- Background scheduled price checks
- More detailed advisor budgeting recommendations
- Better goal prioritization tools
- Public demo mode
- Mobile-first UI improvements
- More extensive automated test coverage
- CI/CD test checks before deployment

---

## Demo Flow

A strong demo walkthrough:

1. Sign up or log in
2. Create a new savings goal
3. Add a target price and timeline
4. Add a contribution toward the goal
5. Add retailer URLs to the goal
6. Run live price check
7. Review updated retailer price summary
8. Ask the Smart Advisor if the purchase makes sense
9. Save the advisor response
10. Open the Advisor page
11. Review saved advisor notes with pagination
12. Toggle dark mode
13. Show the deployed frontend and backend health check

---

## Capstone Requirements Covered

This project demonstrates:

- Full-stack application architecture
- React frontend
- Flask backend
- SQLAlchemy models and relationships
- RESTful API routes
- User authentication
- Protected routes
- CRUD functionality
- External API integration
- Production deployment
- Environment variable management
- PostgreSQL production database
- Frontend build process
- Unit testing support
- Real-world debugging and deployment fixes

---

## Author

Josh Clay

GitHub: https://github.com/JTClay1

Project Repository: https://github.com/JTClay1/build-n-buy

---

## Final Note

Build n' Buy was built to make large purchases feel less chaotic and more intentional. It gives users a practical way to plan before they spend, compare real prices, understand their budget, and get AI-assisted guidance before making a decision.

The app's mission is simple:

Plan smarter. Save first. Buy with confidence.