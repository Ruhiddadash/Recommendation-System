// ==============================
// main.js - Updated Logic
// ==============================

// GLOBALS
let movies = [];            // Currently displayed movies (random 16 or search results)
let selectedMovies = [];    // Array of selected Movie IDs
let currentUser = null;
let allMovies = [];         // All movies fetched from DB

// ==============================
// LOAD MOVIES FROM BACKEND
// ==============================
async function loadMovies() {
    try {
        const response = await fetch("/api/movies/all/");
        allMovies = await response.json();

        // Generate initial 16 random movies
        movies = allMovies
            .sort(() => Math.random() - 0.5)
            .slice(0, 16);

        console.log("Loaded ALL movies:", allMovies.length);
        
        populateMoviesGrid();
        // Clear selected on reload or keep them? 
        // Typically reset on reload unless using localStorage.
        // selectedMovies = []; 
        // updateSelectedGrid(); 

    } catch (error) {
        console.error("Error loading movies:", error);
        showAlert("Could not load movies!", "error");
    }
}

// ==============================
// USER SESSION
// ==============================
function loadUserData() {
    const userData = sessionStorage.getItem('currentUser');
    if (userData) {
        currentUser = JSON.parse(userData);
        updateUserDisplay();
    }
}

function updateUserDisplay() {
    if (currentUser) {
        const userNameElement = document.getElementById('currentUser');
        if (userNameElement) {
            userNameElement.textContent = currentUser.name || (currentUser.email || '').split('@')[0];
        }
    }
}

// ==============================
// POPULATE MAIN GRID
// ==============================
function populateMoviesGrid() {
    const grid = document.getElementById("moviesGrid");
    if (!grid) return;

    grid.innerHTML = "";

    if (movies.length === 0) {
        grid.innerHTML = '<p style="text-align:center; width:100%; color:#888;">No movies found.</p>';
        return;
    }

    movies.forEach(movie => {
        const movieCard = createMovieCard(movie);
        
        // Check if this movie is already selected to apply visual state
        if (selectedMovies.includes(movie.id)) {
            movieCard.classList.add('selected');
        }

        // Click in main grid toggles selection
        movieCard.onclick = () => toggleMovieSelection(movie.id);

        grid.appendChild(movieCard);
    });
}

// Helper to create card HTML
function createMovieCard(movie) {
    const movieCard = document.createElement("div");
    movieCard.className = "movie-card";
    // Store ID for easy access later
    movieCard.dataset.id = movie.id; 

    movieCard.innerHTML = `
        <div class="movie-poster">🎬</div>
        <div class="movie-info">
            <div class="movie-title">${escapeHtml(movie.title)}</div>
            <div class="movie-genre">${escapeHtml(movie.genres || "Unknown Genre")}</div>
        </div>
    `;
    return movieCard;
}

// ==============================
// SELECTION LOGIC
// ==============================

// Unified function to handle selecting/unselecting
function toggleMovieSelection(movieId) {
    const index = selectedMovies.indexOf(movieId);

    if (index > -1) {
        // Already selected -> Remove it
        selectedMovies.splice(index, 1);
        removeSelectionVisuals(movieId);
    } else {
        // Not selected -> Add it (Max 4)
        if (selectedMovies.length >= 4) {
            showAlert('You can select up to 4 movies only!', 'error');
            return;
        }
        selectedMovies.push(movieId);
        addSelectionVisuals(movieId);
    }

    // Update the separate "Selected Movies" grid
    updateSelectedGrid();
    
    // Update button text
    updateRecommendButton();
    
    // Update stats
    const selCount = document.getElementById('selectedCount');
    if (selCount) selCount.textContent = selectedMovies.length;
}

// Updates visuals in the MAIN grid (adds/removes border)
function addSelectionVisuals(movieId) {
    const card = document.querySelector(`#moviesGrid .movie-card[data-id='${movieId}']`);
    if (card) card.classList.add('selected');
}

function removeSelectionVisuals(movieId) {
    const card = document.querySelector(`#moviesGrid .movie-card[data-id='${movieId}']`);
    if (card) card.classList.remove('selected');
}

// ==============================
// SELECTED GRID LOGIC
// ==============================
function updateSelectedGrid() {
    const selectedGrid = document.getElementById("selectedMoviesGrid");
    const selectedSection = document.getElementById("selectedSection");
    
    if (!selectedGrid) return;

    selectedGrid.innerHTML = "";

    // Find the full movie objects for the selected IDs
    // We look in 'allMovies' to ensure we find it even if it's not currently visible in the main random 16 grid
    const selectedMovieObjects = allMovies.filter(m => selectedMovies.includes(m.id));

    if (selectedMovieObjects.length === 0) {
        selectedGrid.innerHTML = '<p style="color:#999; font-style:italic;">No movies selected yet.</p>';
        return;
    }
    
    selectedMovieObjects.forEach(movie => {
        const card = createMovieCard(movie);
        card.classList.add('selected-preview'); // Special style for top section if needed
        
        // Add a "Remove" badge or just click to remove
        const removeBadge = document.createElement("div");
        removeBadge.innerHTML = "❌";
        removeBadge.className = "remove-badge";
        card.appendChild(removeBadge);

        // Clicking here removes it
        card.onclick = () => toggleMovieSelection(movie.id);

        selectedGrid.appendChild(card);
    });
}


// ==============================
// RECOMMENDATIONS
// ==============================
async function getRecommendations() {
    const accessToken = sessionStorage.getItem("accessToken");
    if (!accessToken) {
        showAlert("Please login to get recommendations", "error");
        return;
    }

    if (selectedMovies.length === 0) {
        showAlert("Pick at least 1 movie!", "error");
        return;
    }

    const algorithm = (document.getElementById('algorithmSelect') || {}).value || 'content_based';
    const payload = {
        selected_ids: selectedMovies,
        top_k: 16
    };

    const btn = document.getElementById("getRecommendationsBtn");
    const originalText = btn ? btn.textContent : "Getting...";
    if (btn) { btn.textContent = "Processing..."; btn.disabled = true; }

    try {
        let recommendations = [];
        if (algorithm === "content_based") {
            recommendations = await fetchContentBasedRecommendations(payload, accessToken);
        } else {
            recommendations = await fetchCollaborativeRecommendations(payload, accessToken);
        }

        displayRecommendations(recommendations);
    } catch (err) {
        console.error("Recommendation error:", err);
        showAlert("Recommendation failed: " + (err.message || err), "error");
    } finally {
        if (btn) { btn.textContent = originalText; btn.disabled = false; }
    }
}

async function fetchContentBasedRecommendations(payload, accessToken) {
    const res = await fetch("/api/movies/recommend/content/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`
        },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to fetch content-based");
    return data;
}

async function fetchCollaborativeRecommendations(payload, accessToken) {
    // Placeholder - verify your URL
    const res = await fetch("/api/movies/recommend/collaborative/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${accessToken}`
        },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to fetch collaborative");
    return data;
}

function displayRecommendations(recommendations) {
    const section = document.getElementById('recommendationsSection');
    const grid = document.getElementById('recommendationsGrid');
    if (!section || !grid) return;

    grid.innerHTML = '';
    
    // Sort by score if available
    recommendations.forEach((rec, index) => {
        const card = document.createElement('div');
        card.className = 'recommendation-card';
        card.style.animationDelay = `${index * 0.05}s`;
        
        // Generate stars based on score (assuming score 0-1 or 0-5)
        // Adjust score logic based on your backend. Example: rec.score * 5
        const scoreDisplay = rec.score ? `match: ${(rec.score * 100).toFixed(0)}%` : '';

        card.innerHTML = `
            <div style="font-size: 2rem; margin-bottom: 10px;">🌟</div>
            <h3 class="rec-title">${escapeHtml(rec.title)}</h3>
            <p class="rec-genre">${escapeHtml(rec.genres)}</p>
            <p class="rec-score">${scoreDisplay}</p>
        `;
        grid.appendChild(card);
    });

    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth' });

    const recCount = document.getElementById('recommendationCount');
    if (recCount) recCount.textContent = recommendations.length;
}

// ==============================
// SEARCH & UTILS
// ==============================

function searchMovies() {
    const input = document.getElementById("movieSearchInput");
    const query = input ? input.value.toLowerCase().trim() : "";

    if (!query) {
        // If search cleared, go back to random 16
        // Or keep the current random set? 
        // User asked "Generate initial 16 random". 
        // Usually clearing search brings back the "Discover" view (random)
        movies = allMovies
            .sort(() => Math.random() - 0.5)
            .slice(0, 16);
    } else {
        movies = allMovies.filter(m => 
            m.title.toLowerCase().includes(query) || 
            (m.genres || "").toLowerCase().includes(query)
        ).slice(0, 16); // Limit search results to 16 for performance
    }
    populateMoviesGrid();
}

function escapeHtml(s) {
    if (!s) return "";
    return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function updateRecommendButton() {
    const btn = document.getElementById('getRecommendationsBtn');
    if (btn) {
        btn.textContent = selectedMovies.length > 0
            ? `Get Recommendations (${selectedMovies.length} selected)`
            : 'Get My Recommendations';
    }
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    // Add basic styling for alert if not in CSS
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.left = '50%';
    alertDiv.style.transform = 'translateX(-50%)';
    alertDiv.style.padding = '10px 20px';
    alertDiv.style.borderRadius = '5px';
    alertDiv.style.zIndex = '1000';
    alertDiv.style.color = 'white';
    alertDiv.style.backgroundColor = type === 'error' ? '#ff4757' : '#2ed573';
    alertDiv.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';

    document.body.appendChild(alertDiv);
    setTimeout(() => { alertDiv.remove(); }, 3000);
}

// --- FIXED LOGOUT FUNCTION ---
function logoutUser() {
    // 1. Clear CLIENT-SIDE session
    sessionStorage.removeItem("accessToken");
    sessionStorage.removeItem("currentUser");

    // 2. Clear SERVER-SIDE session and redirect
    // This hits the Django view which performs logout(request) and redirects to login-page
    window.location.href = "/api/accounts/logout/";
}

// --- FIXED AUTH CHECK ---
function checkAuth() {
    const token = sessionStorage.getItem('accessToken');
    if (!token) {
        // If no token, force redirect to login
        window.location.href = "/api/accounts/login-page/";
        return false;
    }
    return true; 
}

// ==============================
// INIT
// ==============================
async function init() {
    await loadMovies();
    loadUserData();
}

document.addEventListener('DOMContentLoaded', init);

// Expose API
window.MovieApp = {
    init,
    toggleMovieSelection, // Exposed as selectMovie in HTML usually
    getRecommendations,
    logout: logoutUser, // Map generic logout to our specific logic
    showAlert,
    checkAuth,
    searchMovies
};

// Map old HTML calls to new function names if necessary
window.selectMovie = toggleMovieSelection;
// Ensure global scope access for the HTML button onclick="logoutUser()"
window.logoutUser = logoutUser;