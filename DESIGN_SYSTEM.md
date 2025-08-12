# OGRDB Design System Implementation Guide

## Overview

This implementation establishes a comprehensive design system for OGRDB built on Bootstrap 5, focusing on consistency, accessibility, and modern visual design. The system introduces CSS custom properties, extended utility classes, and enhanced components that can be applied across all pages.

## What's Been Implemented

### 1. CSS Custom Properties (CSS Variables)
**Location**: `templates/bootstrap5_base.html` (lines 9-102)

**Features**:
- **Brand Colors**: Primary (#188DFB) with light/dark variations
- **Semantic Colors**: Success, warning, danger, info with light variants
- **Typography Scale**: Consistent font sizes, weights, and line heights
- **Spacing Scale**: xs, sm, base, lg, xl spacing units
- **Shadow System**: sm, base, lg shadows plus primary shadow
- **Border Radius**: xs, sm, base, lg, xl radius options
- **Transitions**: fast, base, slow transition timing

**Benefits**:
- Easy theming by changing CSS variables
- Consistent spacing and sizing across all components
- Runtime color scheme switching capability
- Better maintenance and scalability

### 2. Enhanced Utility Classes
**Location**: `static/css/ogrdb-design-system.css`

**Features**:
- **Extended Typography**: .text-xs, .text-xl, .fw-medium, .fw-semibold
- **Enhanced Spacing**: .p-xs, .m-xl, etc. for fine-grained control
- **Flexbox Utilities**: .d-flex-center, .d-flex-between for common layouts
- **Color Extensions**: .text-primary-light, .bg-primary-lightest
- **Shadow Utilities**: .shadow-primary, .shadow-hover

**Benefits**:
- Rapid prototyping without custom CSS
- Consistent spacing and color application
- Mobile-first responsive utilities

### 3. Enhanced Component Styling

#### **Cards**
- Default shadow and border styling
- Hover effects with `.card-hover`
- Color-coded left borders (`.card-primary`, `.card-success`)
- Enhanced `.data-card` component for content display

#### **Buttons**
- Improved focus states and accessibility
- Enhanced hover effects with shadows
- Consistent brand color application

#### **Forms**
- Better focus states with brand colors
- Enhanced form controls with `.form-floating-enhanced`
- Improved input group styling

#### **Tables**
- Consistent header styling
- Enhanced hover states
- Better border and spacing

#### **Modals**
- Rounded corners and better shadows
- Brand-colored headers
- Improved spacing and typography

### 4. Content Layout Components
**Location**: `static/css/ogrdb-design-system.css` (lines 180-270)

**Components**:
- `.content-section`: Standard section padding
- `.hero-section`: Full-width hero areas
- `.section-header`: Consistent section titles
- `.data-card`: Enhanced content cards
- `.stats-grid`: Statistics display grid

### 5. Status Indicators & File Types
**Features**:
- Status badges for published/draft/reviewing/withdrawn
- File type icons for JSON/FASTA/CSV/PDF/ZIP
- Consistent color coding and typography

### 6. Accessibility Enhancements
**Features**:
- Enhanced focus management with `.focus-ring`
- Screen reader utilities
- Keyboard navigation improvements
- High contrast focus states

## How to Use

### 1. In Existing Templates
Replace traditional Bootstrap classes with enhanced versions:

```html
<!-- Before -->
<div class="card">
    <div class="card-body">
        <h5 class="card-title text-primary">Title</h5>
        <p class="card-text">Content</p>
    </div>
</div>

<!-- After -->
<div class="card card-hover card-primary">
    <div class="card-body">
        <h5 class="card-title fw-semibold">Title</h5>
        <p class="card-text text-muted">Content</p>
    </div>
</div>
```

### 2. Using New Components
```html
<!-- Data Display Card -->
<div class="data-card">
    <div class="data-card-header">
        <h6 class="data-card-title">Sequence Information</h6>
        <small class="data-card-subtitle">IGHV1-69*01</small>
    </div>
    <p>Sequence content...</p>
</div>

<!-- Status Indicators -->
<span class="status-badge status-published">
    <i class="bi bi-check-circle"></i>Published
</span>

<!-- File Type Icon -->
<div class="d-flex align-items-center">
    <div class="file-icon file-icon-json">JSON</div>
    <span>AIRR-C Format Download</span>
</div>
```

### 3. Using CSS Custom Properties
```css
/* In custom CSS */
.my-component {
    background-color: var(--ogrdb-primary-lightest);
    border: 1px solid var(--ogrdb-border-light);
    border-radius: var(--ogrdb-border-radius);
    padding: var(--ogrdb-spacer-lg);
    box-shadow: var(--ogrdb-shadow-sm);
}
```

## Testing the Design System

Visit `/design-system-demo` to see all components in action:
- Color palette demonstration
- Typography scale examples
- Card component variations
- Form enhancements
- Status indicators
- Interactive elements

## Benefits for OGRDB

### 1. **Immediate Visual Improvements**
- Modern, professional appearance
- Consistent spacing and colors
- Enhanced visual hierarchy

### 2. **Development Efficiency**
- Rapid component creation with utility classes
- Consistent styling without repetitive CSS
- Easy maintenance and updates

### 3. **User Experience**
- Better accessibility and focus management
- Improved mobile responsiveness
- Clear visual feedback and status indicators

### 4. **Scalability**
- Easy to extend with new components
- Consistent design language across all pages
- Simple theming for future customization

### 5. **Future-Proof**
- Built on Bootstrap 5 best practices
- Modern CSS features (custom properties)
- Easy integration with new front page design

## Next Steps

### Phase 1: Foundation Complete ✅
- [x] CSS custom properties implemented
- [x] Enhanced utility classes created
- [x] Core component styling updated
- [x] Design system demonstration page

### Phase 2: Apply to Existing Pages
- [ ] Update main navigation template
- [ ] Enhance germline sets pages
- [ ] Improve sequence display pages
- [ ] Modernize submission forms

### Phase 3: New Front Page
- [ ] Implement modern front page design
- [ ] Integrate with existing design system
- [ ] Add progressive enhancement features

This foundation provides a solid base for both immediate improvements to existing pages and the implementation of the new modern front page design.
