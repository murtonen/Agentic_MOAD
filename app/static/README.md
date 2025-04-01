# Static Assets

This directory contains static assets for the MOAD AI Query Application:

- `css/` - CSS stylesheets
  - `styles.css` - Main application styles
- `js/` - JavaScript files
  - `script.js` - Main application functionality
- `img/` - Images and icons
  - `favicon.ico` - Application favicon

## Customization

To customize the application appearance:

1. Edit `css/styles.css` to change colors, layout, and styling
2. Edit `js/script.js` to modify client-side behavior
3. Add images to `img/` directory as needed

## CSS Variables

The application uses CSS variables for consistent theming. Main variables are defined at the top of `styles.css`:

```css
:root {
    --primary-color: #0066CC;
    --secondary-color: #0070AD;
    --light-gray: #f8f9fa;
    --border-color: #dee2e6;
    --success-color: #28a745;
    --danger-color: #dc3545;
    --standard-color: #6c757d;
    --pro-color: #0d6efd;
    --pro-plus-color: #6610f2;
    --enterprise-color: #198754;
}
```

Change these values to update the color scheme throughout the application. 