# Email Writing Game

A competitive email-writing game where players compete to write the best emails for specific scenarios, evaluated by AI.

## Features

- **Scenario-based email writing**: Write emails for various communication scenarios
- **AI-powered evaluation**: Uses GPT-4o to grade emails based on clarity, appropriateness, effectiveness, and grammar  
- **Developer mode**: Customize the evaluator prompt to change grading criteria
- **Real-time leaderboard**: Track scores and compare with other players
- **Detailed feedback**: Get comprehensive feedback on your email writing
- **Score breakdown**: Toggle detailed breakdown of evaluation criteria

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get OpenAI API Key**:
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Generate an API key
   - Keep it secure - you'll enter it in the app

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

4. **Open in browser**:
   - The app will automatically open in your default browser
   - Usually at `http://localhost:8501`

## How to Play

1. **Configure the app**:
   - Enter your OpenAI API key in the sidebar
   - Select the evaluator model (GPT-4o)

2. **Read the scenario**:
   - A communication scenario will be displayed
   - You can modify scenarios for different challenges

3. **Write your email**:
   - Craft the best possible email response
   - Consider clarity, tone, and effectiveness

4. **Developer mode** (optional):
   - Modify the evaluator prompt to change grading criteria
   - Experiment with different evaluation approaches

5. **Submit for evaluation**:
   - Enter your player name
   - Click "Submit Email for Evaluation"
   - Wait for AI grading (usually 10-30 seconds)

6. **View results**:
   - See your overall score out of 100
   - Toggle score breakdown for detailed metrics
   - Read AI feedback for improvement tips

7. **Compete**:
   - View the leaderboard to see how you rank
   - Try different approaches to improve your score

## Game Mechanics

### Scoring Criteria
- **Clarity** (0-100): How clear and easy to understand is the message?
- **Appropriateness** (0-100): How appropriate is the tone and content?
- **Effectiveness** (0-100): How likely is the email to achieve its purpose?
- **Grammar** (0-100): Quality of grammar, spelling, and writing

### Leaderboard
- Sorted by overall score (highest first)
- Shows player name, score, and timestamp
- Expandable entries show full email and detailed breakdown
- Persists during the session (resets when server restarts)

## Developer Features

- **Custom evaluator prompts**: Modify how the AI grades emails
- **Model selection**: Currently supports GPT-4o
- **Score breakdown toggle**: Show/hide detailed scoring
- **Leaderboard management**: Clear all entries when needed

## Tips for Better Scores

1. **Be clear and concise**: Avoid ambiguous language
2. **Match the tone**: Consider the relationship and context
3. **Include key information**: Address all aspects of the scenario  
4. **Proofread**: Check grammar and spelling
5. **Call to action**: Make it clear what you want recipients to do

## Technical Notes

- Built with Streamlit for the web interface
- Uses OpenAI API for email evaluation
- Session-based storage (no persistent database)
- Responsive design for different screen sizes 