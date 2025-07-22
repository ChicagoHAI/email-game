# 📧 Email.io: Email Writing Game

An interactive email-writing application where users practice professional communication skills and receive AI-powered feedback on their emails.

[![Streamlit](https://img.shields.io/badge/Streamlit-1.39+-red?style=flat&logo=streamlit)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-1.13+-blue?style=flat&logo=openai)](https://openai.com)
[![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat&logo=python)](https://python.org)

## ✨ Features

### Core Functionality
- **📋 Scenario-based Writing**: Multiple realistic communication scenarios
- **🤖 AI-Powered Evaluation**: GPT-4o generates detailed feedback and scoring
- **👥 Recipient Simulation**: AI generates realistic responses to your emails
- **📊 Custom Rubrics**: Automatic rubric generation tailored to each scenario
- **🎯 Progress Tracking**: View detailed evaluation results and improvement suggestions

### Advanced Features
- **🛠️ Developer Mode**: Customize evaluation criteria and recipient personas
- **📎 File Support**: Upload and reference documents in scenarios
- **⚡ Smart Caching**: Session-based caching for improved performance
- **🎨 Modern UI**: Clean, responsive design with intuitive navigation
- **📱 Mobile Friendly**: Works seamlessly on desktop and mobile devices

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ 
- OpenAI API key ([Get one here](https://platform.openai.com/))

### Installation

1. **Clone or download the project**:
   ```bash
   git clone <repository-url>
   cd email-game
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key**:
   ```bash
   export OPENAI_API_KEY_CLAB="your-api-key-here"
   ```
   
   Or create a `.env` file:
   ```env
   OPENAI_API_KEY_CLAB=your-api-key-here
   ```

4. **Run the application**:
   ```bash
   streamlit run app.py
   ```

5. **Open in browser**:
   - Navigate to `http://localhost:8501`
   - The app will open automatically in most cases

## 🎮 How to Use

### Getting Started
1. **Select a Scenario**: Choose from pre-built scenarios or create your own
2. **Write Your Email**: Craft your response considering the context and goals
3. **Get AI Feedback**: Submit for evaluation and receive detailed scoring
4. **Review Results**: See your email, the recipient's response, and evaluation breakdown
5. **Iterate & Improve**: Try different approaches to improve your communication skills

### Developer Mode
Access advanced customization options:
- **Recipient Personas**: Define how the email recipient should respond
- **Evaluation Criteria**: Customize how emails are scored
- **Scenario Editing**: Modify scenarios in real-time

## 🏗️ Technical Architecture

### Dependencies
- **Streamlit**: `>=1.39.0` - Modern web app framework
- **OpenAI**: `>=1.13.0` - AI API for content generation and evaluation

### Key Components
- **EmailGenerator**: Generates sample emails using GPT-4o
- **EmailEvaluator**: Provides detailed feedback and scoring
- **EmailRecipient**: Simulates realistic recipient responses
- **RubricGenerator**: Creates custom evaluation criteria

### Data Management
- **Session State**: Maintains user data across interactions
- **File System**: Stores scenarios, prompts, and generated rubrics
- **Caching**: Optimizes performance with intelligent caching

## 🧪 Testing

Run the test suite to verify functionality:

```bash
python test_app.py
```

The tests cover:
- ✅ Scenario loading and validation
- ✅ File handling and error cases
- ✅ API key management
- ✅ Core functionality without API calls

## 🚀 Deployment

### Streamlit Community Cloud (Recommended)

1. **Push to GitHub**: Upload your project to a GitHub repository

2. **Deploy**: 
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Set main file: `experiment_scripts/email_game/app.py`

3. **Configure Secrets**:
   ```toml
   OPENAI_API_KEY_CLAB = "your-api-key-here"
   ```

### Alternative Platforms
- **Railway**: Easy deployment with automatic builds
- **Heroku**: Classic platform with custom domains
- **DigitalOcean**: App Platform for scalable hosting
- **Azure/AWS/GCP**: Enterprise cloud deployment

See `DEPLOYMENT.md` for detailed deployment instructions.

## 📊 Performance Features

### Input Validation
- **Character Limits**: Prevents excessively long inputs (5000 chars for scenarios, 3000 for emails)
- **Error Handling**: Graceful error handling with specific exception types
- **API Safety**: Built-in safeguards against API abuse

### Optimization
- **Session Caching**: Rubrics cached to minimize API calls
- **Lazy Loading**: Resources loaded only when needed
- **Error Recovery**: Robust fallback mechanisms

## 🔧 Configuration

### Environment Variables
- `OPENAI_API_KEY_CLAB`: Your OpenAI API key (required)

### Customization Options
- **Models**: Switch between OpenAI models (default: GPT-4o)
- **Temperature**: Adjust AI creativity (default: 0.7 for generation, 0.3 for evaluation)
- **Scenarios**: Add custom scenarios in `/prompts/scenarios/`
- **Rubrics**: Pre-define rubrics in `/rubrics/`

## 💡 Tips for Better Emails

### Writing Strategy
1. **Understand the Context**: Read scenarios carefully and identify key stakeholders
2. **Be Clear & Concise**: Avoid ambiguous language and unnecessary complexity
3. **Match the Tone**: Consider the relationship and formality level required
4. **Include Key Information**: Address all aspects mentioned in the scenario
5. **Proofread**: Check grammar, spelling, and overall coherence
6. **Call to Action**: Make your expectations and next steps clear

### Using AI Assistance
- **Generate Examples**: Use the AI generation feature for inspiration
- **Iterate**: Try multiple approaches to see what works best
- **Learn from Feedback**: Pay attention to specific scoring criteria

## 🛠️ Development

### Project Structure
```
email_game/
├── app.py                 # Main application
├── test_app.py           # Test suite
├── requirements.txt      # Dependencies
├── DEPLOYMENT.md         # Deployment guide
├── .streamlit/           # Streamlit configuration
├── prompts/              # System prompts and scenarios
├── rubrics/              # Pre-defined evaluation rubrics
└── README.md            # This file
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📈 Future Enhancements

### Planned Features
- **User Analytics**: Track learning progress over time
- **Export Options**: Download evaluation reports
- **Team Features**: Group challenges and competitions
- **Advanced AI**: Integration with newer models and capabilities

### Technical Improvements
- **Database Integration**: Persistent user data storage
- **Advanced Caching**: Redis for multi-user scenarios
- **API Rate Limiting**: Production-ready throttling
- **Monitoring**: Performance and usage analytics

## 🐛 Troubleshooting

### Common Issues

**API Key Errors**
- Verify your API key is set correctly
- Check that you have sufficient OpenAI credits
- Ensure the environment variable name is correct

**Import Errors**
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python version compatibility (3.8+)

**File Not Found**
- Ensure you're running from the correct directory
- Verify prompt and scenario files exist

**Performance Issues**
- Check your internet connection for API calls
- Clear browser cache if UI seems slow
- Monitor API usage for rate limiting

### Getting Help
- **Documentation**: Check this README and `DEPLOYMENT.md`
- **Issues**: Report bugs on the project's issue tracker
- **Support**: Contact the development team

## 📄 License

This project is part of the Complex Communication Research Project. See the project documentation for license details.

---

**Built with ❤️ using Streamlit and OpenAI GPT-4o** 

## Running the Application

Run the application using:

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`.

## Developer Features

### URL Navigation (User & Developer Modes)

You can use URL parameters to quickly navigate to specific levels without having to complete all previous levels. This feature automatically unlocks all prerequisite levels in the database and works in both User and Developer modes.

**Usage:**
```
http://localhost:8501/?level=5
```

This will:
1. Automatically switch to User Mode (if no mode selected yet)
2. Unlock all levels from 0 up to the specified level (0, 1, 2, 2.5, 3, 4, 5)
3. Navigate directly to the specified level
4. Update both the database and session state

**Available Levels:**
- `0` - Tutorial Level (Scenario 5.0)
- `1` - Level 1 (Scenario 5.1)  
- `2` - Level 2 (Scenario 5.2)
- `2.5` - Challenge Level (Scenario 5.2.5)
- `3` - Multi-recipient Level (Scenario 5.3)
- `4` - Multi-turn Level (Scenario 5.4) 
- `5` - Forwarded Emails Level (Scenario 5.5)

**Requirements:**
- Must have a valid game session (create or select one first)
- Works in both User and Developer modes (will auto-switch to User Mode if needed)
- Level must exist in the `LEVEL_TO_SCENARIO_MAPPING` configuration

**Examples:**
- Jump to Level 3: `http://localhost:8501/?level=3`
- Jump to Challenge Level: `http://localhost:8501/?level=2.5`
- Jump to final level: `http://localhost:8501/?level=5`

**Note:** This feature is designed for development and testing purposes, allowing you to quickly jump to any level for testing. It works in both User and Developer modes and will unlock all prerequisite levels automatically. 