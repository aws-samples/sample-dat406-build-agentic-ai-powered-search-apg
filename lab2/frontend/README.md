# DAT406 Workshop - Frontend Application

## 🎯 Overview

Modern React + TypeScript frontend for the DAT406 Workshop: **Build Agentic AI-Powered Search with Amazon Aurora PostgreSQL**

This is a production-ready e-commerce search interface showcasing:
- ✨ **Semantic Search** powered by Amazon Titan Embeddings v2
- 🤖 **AI-Powered Recommendations** via Amazon Bedrock
- 🎨 **Modern UI** with React 18 + TypeScript + Tailwind CSS
- ⚡ **Fast Development** using Vite

---

## 📋 Prerequisites

- **Node.js**: 20.x or higher
- **npm**: 10.x or higher
- **Backend API**: Running on `http://localhost:8000`

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_AWS_REGION=us-west-2
```

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at: **http://localhost:5173**

---

## 📦 Available Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build production bundle |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint for code quality checks |
| `npm run type-check` | Run TypeScript type checking |

---

## 🗂️ Project Structure

```
frontend/
├── public/                  # Static assets
├── src/
│   ├── components/         # React components
│   │   ├── Header.tsx     # App header with branding
│   │   ├── SearchBar.tsx  # Search input with filters
│   │   ├── ProductCard.tsx # Product grid item
│   │   ├── ProductModal.tsx # Product detail modal
│   │   └── LoadingSpinner.tsx # Loading indicator
│   │
│   ├── services/          # API and business logic
│   │   ├── api.ts        # Backend API client
│   │   └── types.ts      # TypeScript interfaces
│   │
│   ├── hooks/            # Custom React hooks
│   │   └── useSearch.ts  # Search state management
│   │
│   ├── App.tsx           # Main application component
│   ├── main.tsx          # Application entry point
│   └── index.css         # Global styles + Tailwind
│
├── index.html            # HTML template
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── postcss.config.js     # PostCSS configuration
└── package.json          # Project dependencies
```

---

## 🎨 Key Components

### SearchBar
- Real-time search input
- Category filtering
- Debounced API calls
- Loading states

### ProductCard
- Product image with fallback
- Star ratings
- Stock status indicators
- Price display
- Quick view modal

### ProductModal
- Full product details
- High-resolution images
- Customer reviews
- Stock availability
- External Amazon links

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |
| `VITE_AWS_REGION` | AWS region for services | `us-west-2` |

### Vite Configuration

Key settings in `vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

### Tailwind Configuration

Custom colors in `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          // ... extended palette
          900: '#0c4a6e',
        }
      }
    }
  }
}
```

---

## 🎯 API Integration

### Search Endpoint

```typescript
// POST /api/search
const response = await api.post<SearchResponse>('/search', {
  query: 'laptop',
  limit: 20
})
```

**Request:**
```json
{
  "query": "laptop",
  "limit": 20
}
```

**Response:**
```json
{
  "results": [
    {
      "productId": "B08N5WRWNW",
      "product_description": "Apple MacBook Pro...",
      "price": 1299.99,
      "stars": 4.5,
      "reviews": 12543,
      "similarity_score": 0.92
    }
  ],
  "query": "laptop",
  "count": 15,
  "execution_time": 0.045
}
```

### Product Details Endpoint

```typescript
// GET /api/products/{productId}
const product = await api.get<Product>(`/products/${productId}`)
```

---

## 🎨 Styling Guide

### Tailwind CSS Classes

This project uses **Tailwind CSS** for styling. Common patterns:

```tsx
// Buttons
<button className="px-4 py-2 bg-primary-600 text-white rounded-lg 
                   hover:bg-primary-700 transition-colors">
  Search
</button>

// Cards
<div className="bg-white rounded-lg shadow-md p-6 
                hover:shadow-lg transition-shadow">
  {/* content */}
</div>

// Grid Layout
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  {/* items */}
</div>
```

### CSS Warnings

You may see warnings about `@tailwind` and `@apply` directives in `index.css`. These are **harmless** - they're valid Tailwind syntax that VS Code's CSS linter doesn't recognize.

To suppress them, create `.vscode/settings.json`:

```json
{
  "css.lint.unknownAtRules": "ignore"
}
```

---

## 🔍 TypeScript

### Type Definitions

All types are defined in `src/services/types.ts`:

```typescript
export interface Product {
  productId: string
  product_description: string
  imgurl?: string
  producturl?: string
  stars?: number
  reviews?: number
  price?: number
  category_name?: string
  isbestseller?: boolean
  boughtinlastmonth?: number
  quantity?: number
  similarity_score?: number
}

export interface SearchRequest {
  query: string
  limit?: number
  category?: string
}

export interface SearchResponse {
  results: Product[]
  query: string
  count: number
  execution_time: number
}
```

### Type Checking

Run type checking without emitting files:

```bash
npm run type-check
```

---

## 🐛 Troubleshooting

### Issue: Port 5173 already in use

**Solution:**
```bash
# Kill process on port 5173
npx kill-port 5173

# Or use a different port
npm run dev -- --port 3000
```

### Issue: API connection refused

**Solution:**
1. Verify backend is running: `curl http://localhost:8000/api/health`
2. Check `.env` has correct `VITE_API_URL`
3. Restart dev server after changing `.env`

### Issue: Blank page or white screen

**Solution:**
1. Check browser console for errors
2. Verify all dependencies installed: `npm install`
3. Clear Vite cache: `rm -rf node_modules/.vite`
4. Rebuild: `npm run build`

### Issue: TypeScript errors

**Solution:**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Verify TypeScript version
npx tsc --version

# Run type check
npm run type-check
```

### Issue: Styles not applying

**Solution:**
1. Verify Tailwind is configured: `tailwind.config.js` exists
2. Check PostCSS config: `postcss.config.js` exists
3. Restart dev server
4. Hard refresh browser: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

---

## 📱 Responsive Design

The application is fully responsive with breakpoints:

| Breakpoint | Width | Description |
|------------|-------|-------------|
| `sm` | 640px | Small devices |
| `md` | 768px | Tablets |
| `lg` | 1024px | Laptops |
| `xl` | 1280px | Desktops |
| `2xl` | 1536px | Large screens |

Example usage:

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* 1 column on mobile, 2 on tablet, 4 on desktop */}
</div>
```

---

## 🚀 Production Build

### Build for Production

```bash
npm run build
```

Output: `dist/` folder with optimized static files

### Preview Production Build

```bash
npm run preview
```

### Build Optimization

Vite automatically:
- ✅ Minifies JavaScript and CSS
- ✅ Tree-shakes unused code
- ✅ Code-splits for lazy loading
- ✅ Optimizes images
- ✅ Generates source maps

### Production Checklist

- [ ] Update `.env` with production API URL
- [ ] Run `npm run build`
- [ ] Test production build: `npm run preview`
- [ ] Verify all assets load correctly
- [ ] Check browser console for errors
- [ ] Test on multiple devices/browsers

---

## 🎓 Learning Resources

### Technologies Used

- **React**: https://react.dev
- **TypeScript**: https://www.typescriptlang.org
- **Vite**: https://vitejs.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Lucide Icons**: https://lucide.dev

### Workshop Resources

- **AWS Workshop**: https://workshop.aws
- **Aurora PostgreSQL**: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.AuroraPostgreSQL.html
- **pgvector**: https://github.com/pgvector/pgvector
- **Amazon Bedrock**: https://aws.amazon.com/bedrock

---

## 🤝 Contributing

This is a workshop project for **AWS re:Invent 2024**. 

For questions or issues:
1. Check troubleshooting section above
2. Review workshop documentation
3. Ask workshop instructors

---

## 📄 License

This project is part of the AWS DAT406 Workshop and follows AWS Sample Code License.

---

## 🎉 Happy Building!

Built with ❤️ for AWS re:Invent 2025 by the Aurora PostgreSQL Specialist Solutions Architecture team.

**Workshop**: DAT406 - Build Agentic AI-Powered Search with Amazon Aurora  
**Author**: Shayon Sanyal, Principal WW PostgreSQL Specialist SA