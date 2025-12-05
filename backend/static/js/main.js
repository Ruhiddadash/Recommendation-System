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
            <div class="movie-genre">${escapeHtml(movie.year)}</div>
            <div class="movie-genre">${escapeHtml(movie.genres || "Unknown Genre")}</div>
        </div>
    `;
    return movieCard;
}

// ==========================================
// UI: Modal for Rating Requirement (NEW)
// ==========================================
function showRatingRequirementModal() {
    // Remove if already exists
    const existing = document.getElementById("ratingRequirementModal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "ratingRequirementModal";
    modal.innerHTML = `
        <div class="rating-modal-backdrop"></div>
        <div class="rating-modal-box">
            <h2>🎯 Rate at least one selected movie</h2>
            <p>
                Collaborative filtering compares your ratings with users 
                who liked movies similar to YOU. 
                <br><br>
                To get accurate results, please rate at least <b>one</b> 
                of your selected movies before continuing.
            </p>

            <button id="rateNowBtn" class="btn btn-primary">⭐ Rate movies now</button>
        </div>
    `;

    document.body.appendChild(modal);

    // Action button: scroll user to selected grid
    document.getElementById("rateNowBtn").onclick = () => {
        modal.remove();
        document
            .getElementById("selectedSection")
            .scrollIntoView({ behavior: "smooth" });
    };
}

// ==========================================
// Check rating status from backend (NEW)
// ==========================================
async function checkSelectedMovieRatings() {
    const token = sessionStorage.getItem("accessToken");
    if (!token || selectedMovies.length === 0) return false;

    try {
        const res = await fetch("/api/movies/user-ratings/", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ selected_ids: selectedMovies })
        });

        const data = await res.json();
        if (!res.ok) return false;

        return data.has_rated_selected || false;
    } catch (err) {
        console.error("Error checking ratings:", err);
        return false;
    }
}

// Card for CONTENT-BASED recommendations (simple)
function createContentBasedRecommendationCard(rec, index) {
    const card = document.createElement('div');
    card.className = 'recommendation-card';
    card.style.animationDelay = `${index * 0.05}s`;

    const scoreDisplay = (typeof rec.score === 'number')
        ? `Match: ${(rec.score * 100).toFixed(0)}%`
        : '';

    card.innerHTML = `
        <div class="movie-poster">🎞️</div>
        <div class="rec-inner">
            <h3 class="rec-title">${escapeHtml(rec.title)}</h3>
            <p class="rec-genre">${escapeHtml(rec.year)}</p>
            <p class="rec-genre">${escapeHtml(rec.genres || "")}</p>
            ${scoreDisplay ? `<p class="rec-score">${scoreDisplay}</p>` : ""}
        </div>
    `;

    return card;
}

// Card for COLLABORATIVE FILTERING recommendations (with trust metrics)
function createCollaborativeRecommendationCard(rec, index) {
    const card = document.createElement('div');
    card.className = 'recommendation-card cf';
    card.style.animationDelay = `${index * 0.05}s`;

    card.innerHTML = `
        <div class="movie-poster">🎞️</div>
        <h3 class="rec-title">${escapeHtml(rec.title)}</h3>
        <p class="rec-genre">${escapeHtml(rec.genres || "")}</p>
        <p class="rec-genre">${escapeHtml(rec.year || "")}</p>


        <div class="cf-metrics">
            <div class="metric-line">
                <span>
                    <b>${escapeHtml(rec.badge)}</b>
                </span>
            </div>

            <div class="cf-reason">
                ${escapeHtml(rec.reason)}
            </div>
        </div>
    `;

    return card;
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
    if (!selectedGrid) return;

    selectedGrid.innerHTML = "";

    const selectedMovieObjects = allMovies.filter(m => selectedMovies.includes(m.id));

    if (selectedMovieObjects.length === 0) {
        selectedGrid.innerHTML = '<p style="color:#999; font-style:italic;">No movies selected yet.</p>';
        return;
    }

    selectedMovieObjects.forEach(movie => {
        const card = createMovieCard(movie);

        // Restore click to remove movie selection
        card.onclick = () => toggleMovieSelection(movie.id);

        /* ⭐ RATING SECTION */
        const ratingContainer = document.createElement("div");
        ratingContainer.className = "rating-stars";
        ratingContainer.dataset.movieId = movie.id;

        let starsHTML = "";
        for (let i = 1; i <= 5; i++) {
            starsHTML += `<span class="star" data-star="${i}">★</span>`;
        }

        ratingContainer.innerHTML = starsHTML;
        card.appendChild(ratingContainer);

        /* Prevent card removal if a star is clicked */
        ratingContainer.addEventListener("click", async (e) => {
            if (!e.target.classList.contains("star")) return;

            e.stopPropagation(); // ⛔ prevent toggleMovieSelection()

            const rating = Number(e.target.dataset.star);
            await submitMovieRating(movie.id, rating);
            highlightStars(ratingContainer, rating);
        });

        selectedGrid.appendChild(card);
    });
}



function highlightStars(container, rating) {
    [...container.querySelectorAll(".star")].forEach(star => {
        star.style.color = Number(star.dataset.star) <= rating ? "#ffd700" : "#ccc";
    });
}

async function submitMovieRating(movieId, rating) {
    const token = sessionStorage.getItem("accessToken");
    if (!token) return alert("Session expired. Login again.");

    try {
        const res = await fetch("/api/movies/rate/", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ movie: movieId, rating })
        });

        const data = await res.json();
        if (!res.ok) {
            console.error("Rating error:", data);
            alert("Failed to save rating");
        } else {
            console.log("Rating saved:", data);
        }
    } catch (err) {
        console.error("Error rating movie:", err);
    }
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

    // === NEW LOGIC: Collaborative must have rated selected movie ===
    if (algorithm === "collaborative") {
        const hasRated = await checkSelectedMovieRatings();

        if (!hasRated) {
            showRatingRequirementModal();
            return; // ❗ Stop CF call
        }
    }

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

        displayRecommendations(recommendations, algorithm);
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
    if (!res.ok) {
    return {
        success: false,
        message: data.message || "Collaborative filtering is unavailable",
        reason: data.error_type || null,
        required: data.required_ratings || null,
        current: data.user_current_ratings || null
    };
}

    return data;
}

function displayRecommendations(recommendations, algorithm = 'content_based') {
    const section = document.getElementById('recommendationsSection');
    const grid = document.getElementById('recommendationsGrid');
    if (!section || !grid) return;

    // In case backend wraps data: { recommendations: [...] }
    const recList = Array.isArray(recommendations.recommendations)
        ? recommendations.recommendations
        : recommendations;

    grid.innerHTML = '';

    recList.forEach((rec, index) => {
        let card;
        if (algorithm === 'collaborative') {
            card = createCollaborativeRecommendationCard(rec, index);
        } else {
            card = createContentBasedRecommendationCard(rec, index);
        }
        grid.appendChild(card);
    });

    if (recommendations && recommendations.success === false) {
        MovieApp.showAlert(
            recommendations.message + 
            (recommendations.current !== null 
                ? ` (You have ${recommendations.current}, need ${recommendations.required})`
                : ""
            ), 
            "error"
        );
        return;
    }


    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth' });

    const recCount = document.getElementById('recommendationCount');
    if (recCount) recCount.textContent = recList.length;
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
    sessionStorage.removeItem("accessToken");
    sessionStorage.removeItem("currentUser");
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

// ==========================================================
// Add modal styling directly (optional but convenient)
// ==========================================================
const style = document.createElement("style");
style.textContent = `
.rating-modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.55);
    backdrop-filter: blur(3px);
    z-index: 2000;
    animation: fadeInModal .25s ease-out;
}

.rating-modal-box {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    z-index: 3000;
    width: 420px;
    padding: 28px;
    border-radius: 14px;
    text-align: center;
    box-shadow: 0px 8px 24px rgba(0,0,0,.28);
    animation: slideUpModal .25s ease-out;
}

.rating-modal-box h2 {
    margin-bottom: 12px;
    color: #333;
}

.rating-modal-box p {
    margin-bottom: 22px;
    font-size: 0.95rem;
    color: #666;
    line-height: 1.5;
}

@keyframes fadeInModal {
    0% { opacity: 0 }
    100% { opacity: 1 }
}
@keyframes slideUpModal {
    0% { transform: translate(-50%, -40%); opacity: 0 }
    100% { transform: translate(-50%, -50%); opacity: 1 }
}
`;
document.head.appendChild(style);