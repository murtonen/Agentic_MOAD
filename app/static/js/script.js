/**
 * MOAD AI Query Application
 * Client-side functionality for querying and displaying results
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const queryForm = document.getElementById('query-form');
    const queryInput = document.getElementById('query-input');
    const bypassCache = document.getElementById('bypass-cache');
    const submitBtn = document.getElementById('submit-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultContainer = document.getElementById('result-container');
    const summaryContent = document.getElementById('summary-content');
    const sourceSlides = document.getElementById('source-slides');
    const processingTime = document.getElementById('processing-time');
    const verifiedBadge = document.getElementById('verified-badge');
    const exampleQueries = document.querySelectorAll('.example-query');

    // Handle form submission
    queryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await submitQuery(queryInput.value);
    });

    // Handle example query clicks
    exampleQueries.forEach(example => {
        example.addEventListener('click', (e) => {
            e.preventDefault();
            const queryText = example.textContent;
            queryInput.value = queryText;
            submitQuery(queryText);
        });
    });

    // Function to submit a query to the backend
    async function submitQuery(query) {
        if (!query.trim()) return;

        // Show loading indicator and hide results
        loadingIndicator.style.display = 'block';
        resultContainer.style.display = 'none';
        submitBtn.disabled = true;

        try {
            const startTime = performance.now();
            
            // Prepare query parameters
            const params = new URLSearchParams({
                query: query,
                bypass_cache: bypassCache.checked
            });

            // Send query to backend
            const response = await fetch(`/api/query?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Query failed');
            }

            const data = await response.json();
            const endTime = performance.now();
            const processingTimeValue = ((endTime - startTime) / 1000).toFixed(2);

            // Update processing time
            processingTime.textContent = `Processing time: ${processingTimeValue}s`;
            processingTime.style.display = 'block';

            // Update verification badge
            if (data.cached) {
                verifiedBadge.textContent = 'Cached';
                verifiedBadge.style.backgroundColor = '#6c757d';
            } else {
                verifiedBadge.textContent = 'Verified';
                verifiedBadge.style.backgroundColor = '#28a745';
            }

            // Display the results
            displayResults(data);
        } catch (error) {
            console.error('Error:', error);
            summaryContent.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle"></i> An error occurred while processing your query. Please try again.
                </div>
            `;
            sourceSlides.innerHTML = '';
            resultContainer.style.display = 'block';
        } finally {
            // Hide loading indicator and enable submit button
            loadingIndicator.style.display = 'none';
            submitBtn.disabled = false;
        }
    }

    // Function to display results
    function displayResults(data) {
        // Format and display summary
        summaryContent.innerHTML = formatSummary(data.summary);
        
        // Format and display sources
        if (data.sources && data.sources.length > 0) {
            sourceSlides.innerHTML = '';
            data.sources.forEach(source => {
                const sourceElement = document.createElement('div');
                sourceElement.className = 'source-item';
                sourceElement.innerHTML = `
                    <div class="d-flex justify-content-between align-items-top">
                        <div>
                            <strong>${source.title || 'Slide'}</strong>
                            <p class="mb-0">${source.content}</p>
                        </div>
                        ${source.slide_number ? `<span class="badge bg-secondary">Slide ${source.slide_number}</span>` : ''}
                    </div>
                `;
                sourceSlides.appendChild(sourceElement);
            });
        } else {
            sourceSlides.innerHTML = '<p class="text-muted">No source information available</p>';
        }

        // Show the result container
        resultContainer.style.display = 'block';
    }

    // Function to format summary with license features highlighting
    function formatSummary(summary) {
        // Replace checkmarks and x marks for features
        summary = summary.replace(/✓/g, '<i class="fas fa-check feature-available"></i>');
        summary = summary.replace(/✗/g, '<i class="fas fa-times feature-unavailable"></i>');
        
        // Add license tier styling
        const licenseTypes = ['Standard', 'Professional', 'Pro Plus', 'Enterprise'];
        
        licenseTypes.forEach(license => {
            const regex = new RegExp(`(${license} (License|Tier|Features):)`, 'g');
            summary = summary.replace(regex, `<h3 class="license-heading">$1</h3>`);
        });
        
        // Convert newlines to paragraphs
        summary = summary.split('\n\n').map(para => {
            if (para.trim()) {
                return `<p>${para.replace(/\n/g, '<br>')}</p>`;
            }
            return '';
        }).join('');
        
        return summary;
    }
}); 