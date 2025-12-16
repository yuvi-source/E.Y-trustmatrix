const path = require('path');

module.exports = {
  entry: './src/index.jsx',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'bundle.js',
    publicPath: '/',
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react'],
          },
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  resolve: {
    extensions: ['.js', '.jsx'],
  },
  devServer: {
    static: {
      directory: path.join(__dirname, 'public'),
    },
    historyApiFallback: true,
    port: 3020,
    proxy: [
      {
        context: ['/stats', '/providers', '/manual-review', '/run-batch', '/health', '/reports', '/explain'],
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 600000,
        proxyTimeout: 600000,
        onProxyRes: (proxyRes, req, res) => {
          // Handle binary responses (PDFs)
          if (req.url.startsWith('/reports')) {
            proxyRes.headers['content-type'] = 'application/pdf';
          }
        },
      },
    ],
  },
};
