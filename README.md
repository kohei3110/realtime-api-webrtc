# Azure OpenAI Realtime API Demo

This React application demonstrates the use of Azure OpenAI's Realtime API with WebRTC for audio communication.

## Security Warning

⚠️ **IMPORTANT**: This demo includes API keys directly in the `.env` file for demonstration purposes. In a production environment, you should **NEVER** include API keys directly in your client-side code. Instead, use a secure backend service to generate ephemeral keys.

## Environment Setup

This application uses environment variables to store configuration. Create a `.env` file in the project root with the following variables:

```
REACT_APP_WEBRTC_URL=your_webrtc_url
REACT_APP_SESSIONS_URL=your_sessions_url
REACT_APP_API_KEY=your_api_key
REACT_APP_DEPLOYMENT=your_deployment_name
REACT_APP_VOICE=your_voice_name
```

Make sure the WebRTC URL region matches the region of your Azure OpenAI resource.

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

## Features

- Real-time audio communication with Azure OpenAI
- Function calling capabilities
- WebRTC-based communication

## How it Works

1. The application establishes a session with Azure OpenAI Realtime API
2. It creates a WebRTC connection for audio communication
3. The data channel is used for exchanging information between the client and the model
4. The application provides function calling capabilities that the AI model can use

## Functions Available to the AI

- `getPageHTML`: Gets the HTML for the current page
- `changeBackgroundColor`: Changes the background color of the page
- `changeTextColor`: Changes the text color of the page

## Production Deployment

For a production environment:

1. Move the API key and session management to a secure backend service
2. Implement proper authentication and authorization
3. Add error handling and retry logic for better reliability
4. Consider implementing a backend proxy for WebRTC connections

## Learn More

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

To learn more about Azure OpenAI, visit the [Azure OpenAI Service documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/).
