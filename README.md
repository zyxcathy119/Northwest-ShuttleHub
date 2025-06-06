# Northwest Shuttlehub: Member Match System for Northwest Badminton

## Target Users

- **Badminton Club Members** who want to book courts, find opponents, and track their playing progress
- **Players of All Levels** from beginners to advanced players looking for suitable matches
- **Club Administrators** managing court bookings and player statistics

## Key Features

### 🔐 **User Authentication System**
- Secure user registration with email and skill level validation
- Login/logout functionality with session management
- Password hashing for security

### 👤 **Player Profile Management**
- Comprehensive player profiles with detailed information
- Skill level tracking (Beginner, Intermediate, Advanced)
- Player statistics including win rate, total matches, and achievements
- Rich profile data including playing style, favorite shots, and personal goals

### 🏸 **Advanced Court Booking System**
- Real-time court availability checking
- Smart time slot validation (prevents past bookings)
- Interactive booking interface with player selection
- Booking management (view, update, delete)
- Opponent assignment and match coordination

### 🎯 **Player Matching & Discovery**
- Time-based player availability system
- Skill-level appropriate opponent matching
- Detailed player cards with statistics and playing information
- Smart matching algorithm considering player preferences and availability

### 📊 **Progress Tracking & Analytics**
- Comprehensive match history tracking
- Win/loss statistics with detailed scorekeeping
- Performance analytics with monthly trends
- Skill metrics analysis (Consistency, Power, Speed, Technique, Strategy, Endurance)
- Interactive charts and visualizations

### 🏆 **Ranking System**
- Dynamic player rankings based on multiple factors
- Tier-based classification (Champion, Expert, Advanced, Intermediate, Beginner)
- Advanced scoring algorithm considering win rate, activity, and match frequency
- Public leaderboard with detailed player statistics

### 🎨 **Modern UI/UX Design**
- Responsive design that works on all devices
- Modern card-based interface
- Interactive elements with smooth animations
- Professional color scheme and typography
- Intuitive navigation and user flow

## Technical Stack

- **Backend**: Python Flask with SQLite database
- **Frontend**: HTML5, CSS3, JavaScript
- **Authentication**: Werkzeug security for password hashing
- **Database**: SQLite with comprehensive schema
- **Deployment**: Configurable for various hosting platforms

## Current Status (Week 9 Update)

### ✅ **Completed Features**
- ✅ Complete user authentication system
- ✅ Advanced court booking with real-time validation
- ✅ Comprehensive player profile system
- ✅ Intelligent player matching algorithm
- ✅ Full progress tracking with analytics
- ✅ Dynamic ranking system with tier classification
- ✅ Modern responsive UI design
- ✅ Score recording and match result tracking
- ✅ Database migration system for safe updates
- ✅ Sample data generation for testing

### 🎯 **Recent Improvements (Week 9)**
- **New Modern Styling**: Complete UI overhaul with professional design
- **Enhanced Booking System**: Improved court booking logic with better validation
- **Data System Polish**: Comprehensive player data with rich profiles
- **Bug Fixes**: Resolved logical issues in scoring and booking systems
- **Performance Optimization**: Database queries and UI responsiveness improvements

## Installation & Setup

```bash
# Clone the repository
git clone https://github.com/zyxcathy119/Northwest-ShuttleHub.git
cd Northwest-ShuttleHub

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at `http://localhost:5000`

## Database Schema

The application uses SQLite with the following main tables:
- **users**: User authentication and basic information
- **players**: Detailed player profiles and statistics
- **bookings**: Court reservations and match records

## API Endpoints

- `/api/available-players`: Get available players for time-based matching
- Authentication routes: `/register`, `/login`, `/logout`
- Booking management: `/book-courts`, `/delete-booking`, `/update-opponent`
- Score tracking: `/set-scores`, `/set-result`

## Future Enhancements

1. **Advanced Features**
   - Tournament organization system
   - Group booking capabilities
   - Coach-student matching
   - Advanced analytics dashboard

2. **Technical Improvements**
   - Real-time notifications
   - Mobile app development
   - Integration with external booking systems
   - Advanced search and filtering

## Project Timeline

| Phase                     | Duration    | Status          | Completion    |
|---------------------------|-------------|-----------------|---------------|
| Discovery & Planning      | Week 1      | ✅ Completed    | April 2024    |
| Design & Wireframing      | Week 2-3    | ✅ Completed    | May 2024      |
| Core Development          | Week 4-6    | ✅ Completed    | May 2024      |
| Feature Implementation    | Week 7-8    | ✅ Completed    | June 2024     |
| **UI/UX Enhancement**     | **Week 9**  | **✅ Completed** | **June 2024** |
| **System Polish & Debug** | **Week 9**  | **✅ Completed** | **June 2024** |
| Final Testing & Launch    | Week 10     | 🔄 In Progress  | July 2024     |

## Contact Information

**Project Repository**: https://github.com/zyxcathy119/Northwest-ShuttleHub.git  
**Client**: Yuxin Zhang  
**Email**: zyx119@uw.edu  
**Developer**: Yifan Li  
**Email**: yifanli8@uw.edu  

---

*This project demonstrates a full-stack web application with modern design principles, comprehensive functionality, and scalable architecture suitable for badminton club management.*
