# 3-Track Aluminum Window Calculator - Technical Specification

## Project Overview

A comprehensive **3-Track Aluminum Window Price Calculator** for aluminum window fabrication shops. This system calculates the material cost, weight, and total fabrication price for 3-track aluminum sliding windows (1.5mm thickness).

---

## 🎯 Features

### 1. **3-Track Window Calculator**
- Real-time price calculation based on dimensions
- Support for Color (Powder Coated) and Silver (Anodized) aluminum finishes
- Checkbox-based material selection (customer can choose what to include)
- Detailed cost breakdown for each component
- Print quote functionality

### 2. **Admin Panel**
- Secure login/authentication
- Dashboard with quick stats
- Material rate management (editable prices)
- Category & Product management
- Invoice generation and viewing
- Labor cost configuration

### 3. **Public Website**
- Homepage with product categories
- Product detail pages
- Contact information

---

## 📊 Database Schema (MongoDB)

### Collection: `admins`
```javascript
{
  _id: ObjectId,
  username: String,          // Required, unique
  passwordHash: String,      // bcrypt hashed
  createdAt: Date
}
```

### Collection: `material_rates`
```javascript
{
  _id: ObjectId,
  key: String,               // Unique identifier (e.g., 'alu_color')
  value: Number,             // Price in INR
  label: String,             // Display label
  updatedAt: Date
}
```

**Default Material Rates:**
| Key | Default Value | Label |
|-----|---------------|-------|
| `alu_color` | 410 | Aluminum Color (Rs/kg) |
| `alu_silver` | 360 | Aluminum Silver (Rs/kg) |
| `glass` | 45 | Glass (Rs/sqft) |
| `glass_rubber` | 10 | Glass Rubber (Rs/ft) |
| `track_rubber` | 80 | Track Rubber (Rs/window) |
| `mosquito_net` | 10 | Mosquito Net (Rs/sqft) |
| `u_channel` | 100 | U-Channel (Rs/window) |
| `screw` | 80 | Screw (Rs/window) |
| `lock` | 170 | Lock (Rs/unit) |
| `bearing` | 10 | Bearing (Rs/unit) |
| `labour_min` | 350 | Labour Minimum (Rs) |
| `labour_sqft` | 24 | Labour (Rs/sqft) |

### Collection: `categories`
```javascript
{
  _id: ObjectId,
  name: String,
  createdAt: Date
}
```

### Collection: `products`
```javascript
{
  _id: ObjectId,
  name: String,
  description: String,
  imageUrl: String,
  pricePerSqft: Number,
  categoryId: ObjectId,      // Reference to categories
  createdAt: Date
}
```

### Collection: `invoices`
```javascript
{
  _id: ObjectId,
  customerName: String,
  customerPhone: String,
  customerAddress: String,
  productId: ObjectId,
  productName: String,       // Snapshot at time of booking
  heightFt: Number,
  widthFt: Number,
  quantity: Number,
  sqftPriceAtBooking: Number, // Snapshot
  totalAmount: Number,
  createdAt: Date
}
```

---

## 🧮 Calculation Logic

### Base Data (1×1 Window = 1 sq.ft)

For a **1 ft × 1 ft** window with **1.5mm thickness**:

| Component | Length (ft) | Weight (kg) |
|-----------|-------------|-------------|
| 3 Track Top | 3 ft | 1.00 kg |
| 3 Track Bottom | 1 ft | 0.34 kg |
| Handle Section | 2 ft | 0.31 kg |
| Interlock | 4 ft | 0.70 kg |
| Shutter Bottom | 3 ft | 0.45 kg |
| **Total** | - | **2.80 kg** |

### Weight Calculation Formula

```javascript
/**
 * Calculate aluminum weight for any window dimension
 * @param {number} width - Width in feet
 * @param {number} height - Height in feet
 * @returns {number} - Total weight in kg
 */
function calculateWeight(width, height) {
    // Derived formula: Weight = (1.123 × Width) + (1.677 × Height)
    // 
    // How these constants were derived:
    // - 1×1 window weighs 2.8 kg
    // - 3×1 window weighs 5.05 kg (approx)
    // - Difference of 2 ft width adds 2.25 kg → 1.125 kg/ft width
    // - Remaining weight for height: 2.8 - 1.123 = 1.677 kg/ft height
    
    const widthFactor = 1.123;  // kg per ft of width
    const heightFactor = 1.677; // kg per ft of height
    
    return (widthFactor * width) + (heightFactor * height);
}
```

### Complete Price Calculation

```javascript
/**
 * Calculate complete window price
 * @param {number} width - Width in feet
 * @param {number} height - Height in feet
 * @param {string} finishType - 'color' or 'silver'
 * @param {object} rates - Material rates from database
 * @param {object} selectedItems - Object with boolean flags for each component
 * @returns {object} - Detailed price breakdown
 */
function calculateWindowPrice(width, height, finishType, rates, selectedItems) {
    const area = width * height;
    const perimeter = 2 * (width + height);
    
    // 1. ALUMINUM WEIGHT & COST
    const totalWeight = (1.123 * width) + (1.677 * height);
    const aluRate = finishType === 'color' ? rates.alu_color : rates.alu_silver;
    const aluminumCost = Math.round(totalWeight * aluRate);
    
    // 2. GLASS COST
    // Glass covers the full window area
    const glassCost = Math.round(area * rates.glass);
    
    // 3. GLASS RUBBER COST
    // Formula: (2 × Width) + (4 × Height) feet
    // Why: 2 glass panels need rubber on all 4 sides vertically (4H) 
    //      and top/bottom horizontally (2W)
    const rubberLength = (2 * width) + (4 * height);
    const glassRubberCost = Math.round(rubberLength * rates.glass_rubber);
    
    // 4. TRACK RUBBER COST
    // Fixed per window
    const trackRubberCost = rates.track_rubber;
    
    // 5. MOSQUITO NET COST
    // Net covers 50% of window area (one sliding panel equivalent)
    const netArea = area * 0.5;
    const mosquitoNetCost = Math.round(netArea * rates.mosquito_net);
    
    // 6. U-CHANNEL COST
    // Fixed per window
    const uChannelCost = rates.u_channel;
    
    // 7. LOCK COST
    // Fixed per window
    const lockCost = rates.lock;
    
    // 8. BEARING COST
    // 6 bearings per window (3 panels × 2 bearings each)
    const bearingCost = 6 * rates.bearing;
    
    // 9. SCREW COST
    // Fixed per window
    const screwCost = rates.screw;
    
    // 10. LABOUR COST
    // Uses larger of: minimum charge OR per-sqft rate
    const labourCost = Math.max(rates.labour_min, Math.round(area * rates.labour_sqft));
    
    // CALCULATE TOTALS BASED ON SELECTED ITEMS
    let materialsTotal = 0;
    if (selectedItems.glass) materialsTotal += glassCost;
    if (selectedItems.glassRubber) materialsTotal += glassRubberCost;
    if (selectedItems.trackRubber) materialsTotal += trackRubberCost;
    if (selectedItems.mosquitoNet) materialsTotal += mosquitoNetCost;
    if (selectedItems.uChannel) materialsTotal += uChannelCost;
    if (selectedItems.lock) materialsTotal += lockCost;
    if (selectedItems.bearing) materialsTotal += bearingCost;
    if (selectedItems.screw) materialsTotal += screwCost;
    
    const labourTotal = selectedItems.labour ? labourCost : 0;
    
    const grandTotal = aluminumCost + materialsTotal + labourTotal;
    
    return {
        dimensions: { width, height, area },
        weight: {
            total: totalWeight.toFixed(2),
            unit: 'kg'
        },
        breakdown: {
            aluminum: {
                weight: totalWeight.toFixed(2),
                rate: aluRate,
                finishType,
                cost: aluminumCost
            },
            glass: { area, rate: rates.glass, cost: glassCost },
            glassRubber: { length: rubberLength, rate: rates.glass_rubber, cost: glassRubberCost },
            trackRubber: { cost: trackRubberCost },
            mosquitoNet: { area: netArea, rate: rates.mosquito_net, cost: mosquitoNetCost },
            uChannel: { cost: uChannelCost },
            lock: { cost: lockCost },
            bearing: { quantity: 6, rate: rates.bearing, cost: bearingCost },
            screw: { cost: screwCost },
            labour: { area, rate: rates.labour_sqft, minimum: rates.labour_min, cost: labourCost }
        },
        totals: {
            aluminum: aluminumCost,
            materials: materialsTotal,
            labour: labourTotal,
            grandTotal
        }
    };
}
```

---

## 🔌 API Endpoints

### Authentication

#### POST `/api/auth/login`
```javascript
// Request
{ "username": "admin", "password": "admin123" }

// Response (200)
{ "success": true, "token": "JWT_TOKEN", "user": { "id": "...", "username": "admin" } }

// Response (401)
{ "success": false, "message": "Invalid credentials" }
```

#### POST `/api/auth/logout`
```javascript
// Response (200)
{ "success": true, "message": "Logged out successfully" }
```

---

### Material Rates

#### GET `/api/rates`
```javascript
// Response (200)
{
  "success": true,
  "data": {
    "alu_color": 410,
    "alu_silver": 360,
    "glass": 45,
    // ... all other rates
  }
}
```

#### PUT `/api/rates` (Protected - Admin only)
```javascript
// Request
{
  "alu_color": 420,
  "glass": 50
  // ... only include rates to update
}

// Response (200)
{ "success": true, "message": "Rates updated successfully" }
```

---

### Calculator

#### POST `/api/calculator/calculate`
```javascript
// Request
{
  "width": 4,
  "height": 4,
  "finishType": "color",
  "selectedItems": {
    "glass": true,
    "glassRubber": true,
    "trackRubber": true,
    "mosquitoNet": true,
    "uChannel": true,
    "lock": true,
    "bearing": true,
    "screw": true,
    "labour": true
  }
}

// Response (200)
{
  "success": true,
  "data": {
    "dimensions": { "width": 4, "height": 4, "area": 16 },
    "weight": { "total": "11.20", "unit": "kg" },
    "breakdown": {
      "aluminum": { "weight": "11.20", "rate": 410, "finishType": "color", "cost": 4592 },
      "glass": { "area": 16, "rate": 45, "cost": 720 },
      // ... all components
    },
    "totals": {
      "aluminum": 4592,
      "materials": 1425,
      "labour": 384,
      "grandTotal": 6401
    }
  }
}
```

---

### Categories

#### GET `/api/categories`
#### POST `/api/categories` (Protected)
#### PUT `/api/categories/:id` (Protected)
#### DELETE `/api/categories/:id` (Protected)

---

### Products

#### GET `/api/products`
#### GET `/api/products/:id`
#### POST `/api/products` (Protected)
#### PUT `/api/products/:id` (Protected)
#### DELETE `/api/products/:id` (Protected)

---

### Invoices

#### GET `/api/invoices` (Protected)
#### GET `/api/invoices/:id` (Protected)
#### POST `/api/invoices` (Protected)

---

## 📁 Recommended MERN Project Structure

```
aluminium-calculator/
├── backend/
│   ├── config/
│   │   └── db.js                 # MongoDB connection
│   ├── controllers/
│   │   ├── authController.js
│   │   ├── ratesController.js
│   │   ├── calculatorController.js
│   │   ├── categoryController.js
│   │   ├── productController.js
│   │   └── invoiceController.js
│   ├── middleware/
│   │   └── authMiddleware.js     # JWT verification
│   ├── models/
│   │   ├── Admin.js
│   │   ├── MaterialRate.js
│   │   ├── Category.js
│   │   ├── Product.js
│   │   └── Invoice.js
│   ├── routes/
│   │   ├── authRoutes.js
│   │   ├── ratesRoutes.js
│   │   ├── calculatorRoutes.js
│   │   ├── categoryRoutes.js
│   │   ├── productRoutes.js
│   │   └── invoiceRoutes.js
│   ├── utils/
│   │   └── calculations.js       # All calculation logic here
│   ├── .env
│   ├── server.js
│   └── package.json
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Calculator/
│   │   │   │   ├── DimensionInput.jsx
│   │   │   │   ├── FinishTypeToggle.jsx
│   │   │   │   ├── MaterialCheckboxes.jsx
│   │   │   │   ├── PriceBreakdown.jsx
│   │   │   │   └── TotalDisplay.jsx
│   │   │   ├── Admin/
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── RatesEditor.jsx
│   │   │   │   └── InvoiceTable.jsx
│   │   │   └── common/
│   │   │       ├── Navbar.jsx
│   │   │       └── Modal.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Calculator.jsx
│   │   │   ├── AdminLogin.jsx
│   │   │   └── AdminDashboard.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   ├── services/
│   │   │   └── api.js            # Axios instance
│   │   ├── utils/
│   │   │   └── calculations.js   # Same logic for preview
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
└── README.md
```
