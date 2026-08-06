// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/* eslint-env node */
const webpack = require('webpack');
const HtmlWebpackPlugin = require("html-webpack-plugin");
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CopyPlugin = require('copy-webpack-plugin');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const path = require('path');

// Path constants
const APP_PATH = path.resolve(__dirname, 'src');
const BUILD_PATH = path.resolve(__dirname, 'dist');

// disambiguates webpack.config.js between development and production builds
// export a function instead of configuration object to determine 'development'
// vs 'production' modes for plugins
// it's possible to look at the command line arguments as well by using
//    module.exports = (env, argv) => { ... }
// https://webpack.js.org/guides/environment-variables/
module.exports = env => {

  console.log(JSON.stringify(env));

  const DEV_MODE = env.NODE_ENV !== 'production';
  const PUBLIC_PATH = '/';  // root path for the single-profile reference implementation (leading + trailing '/')
  console.log('NODE_ENV ? ', env.NODE_ENV);
  console.log('DEV_MODE ? ', DEV_MODE);

  return {
    // refer to https://webpack.js.org/configuration/mode/
    mode: DEV_MODE ? 'development' : 'production',

    // refer to https://webpack.js.org/configuration/entry-context/
    entry: {
      app: path.join(APP_PATH, 'index.tsx'),
    },

    // refer to https://webpack.js.org/configuration/output/
    output: {
      path: BUILD_PATH,
      filename: DEV_MODE ? '[name].js' : '[name].[contenthash].js',
      publicPath: PUBLIC_PATH, // when specifying sub paths, path should contain leading and trailing '/'
      clean: true
    },

    // refer to https://webpack.js.org/configuration/resolve/
    resolve: {
      extensions: ['.tsx', '.ts', '.js', '.jsx'],
      // polyfills for node modules in webpack 5 if needed
      fallback: {
        'stream': require.resolve('stream-browserify'),
        'crypto': require.resolve('crypto-browserify')
      }
    },

    // refer to https://webpack.js.org/configuration/stats/#statschildren
    stats: {
      children: true,
      errorDetails: true
    },

    // refer to https://webpack.js.org/configuration/optimization/
    optimization: {
      splitChunks: {
        chunks: 'all'
      }
    },

    // refer to https://webpack.js.org/configuration/module/
    module: {
      rules: [
        {
          test: /\.(ts|tsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader'
          }
        },
        // css-loader bundles all the css files into one file
        {
          test: /\.css$/,
          use: [
            DEV_MODE ? 'style-loader' : MiniCssExtractPlugin.loader,
            'css-loader'
          ]
        },
        /*
         * webpack v5 - Asset Modules
         * refer to https://webpack.js.org/guides/asset-modules/
         */
        // handle resource assets - images
        {
          test: /\.(png|jpg|jpeg|gif)$/i,
          type: 'asset/resource',
        },
        // handle inline assets - fonts
        {
          test: /\.(woff|woff2|eot|ttf|otf)$/i,
          type: 'asset/resource',
        },
        /*
         * SVG loader as React Component: https://react-svgr.com/docs/webpack/
         */
        {
          test: /\.svg$/i,
          issuer: /\.[jt]sx?$/,
          use: ['@svgr/webpack'],
        }
      ]
    },

    // refer to https://webpack.js.org/configuration/devtool/#devtool
    // another option is to use 'nosources-source-map' in 'production' mode
    devtool: DEV_MODE ? 'eval-source-map' : 'hidden-source-map',

    // refer to https://webpack.js.org/configuration/dev-server/#devserver
    devServer: {
      devMiddleware: {
        writeToDisk: true
      },
      static: {
        directory: APP_PATH,
        publicPath: '/', // The bundled files will be available in the browser under this path.
      },
      port: 3000,
      hot: true,
      historyApiFallback: {
        index: PUBLIC_PATH, // Rewrite unknown paths to the SPA entry point
      },
      open: [PUBLIC_PATH], // Open browser at PUBLIC_PATH
    },

    // refer to https://webpack.js.org/configuration/plugins/
    plugins: [
      // https://webpack.js.org/plugins/html-webpack-plugin/#root
      // simplifies creation of HTML files to serve your webpack bundles
      new HtmlWebpackPlugin({
        inject: true,
        template: path.join(APP_PATH, 'index.html'),
        title: 'Chat Bot'
      }),

      // https://webpack.js.org/plugins/mini-css-extract-plugin/#root
      new MiniCssExtractPlugin({
        filename: DEV_MODE ? '[name].css' : '[name].[contenthash].css',
        chunkFilename: DEV_MODE ? '[id].css' : '[id].[contenthash].css'
      }),

      // https://webpack.js.org/plugins/copy-webpack-plugin/#getting-started
      // copies individual files or entire directories, which already exist, to the build directory.
      new CopyPlugin({
        patterns: [
          { from: 'public', to: '.' },
        ],
      }),

      // https://github.com/danethurber/webpack-manifest-plugin
      // https://webpack.js.org/guides/output-management/
      // generate an asset manifest.
      new WebpackManifestPlugin({
        fileName: 'asset-manifest.json'
      }),

      // https://webpack.js.org/plugins/define-plugin/#root
      // Define global constants which can be configured at compile time
      new webpack.DefinePlugin({
        'process.env.NODE_ENV': JSON.stringify(env.NODE_ENV),
        // WebSocket URL - set via environment variable or tasks.json
        // For AgentCore deployment, use the custom domain (e.g., wss://your-gateway.example.com).
        // For local development, use: ws://localhost:8081
        '__WEBSOCKET_URL__': env.WEBSOCKET_URL ? JSON.stringify(env.WEBSOCKET_URL) : process.env.WEBSOCKET_URL ? JSON.stringify(process.env.WEBSOCKET_URL) : JSON.stringify(""),
        '__DEV_MODE__': DEV_MODE,
        // Authentication variables (IdP-agnostic OIDC — supports Auth0, Okta, Cognito, Entra ID)
        '__OIDC_AUTHORITY__': env.OIDC_AUTHORITY ? JSON.stringify(env.OIDC_AUTHORITY) : process.env.OIDC_AUTHORITY ? JSON.stringify(process.env.OIDC_AUTHORITY) : JSON.stringify(''),
        '__OIDC_CLIENT_ID__': env.OIDC_CLIENT_ID ? JSON.stringify(env.OIDC_CLIENT_ID) : process.env.OIDC_CLIENT_ID ? JSON.stringify(process.env.OIDC_CLIENT_ID) : JSON.stringify(''),
        '__OIDC_AUDIENCE__': env.OIDC_AUDIENCE ? JSON.stringify(env.OIDC_AUDIENCE) : process.env.OIDC_AUDIENCE ? JSON.stringify(process.env.OIDC_AUDIENCE) : JSON.stringify(''),
        '__OIDC_SCOPE__': env.OIDC_SCOPE ? JSON.stringify(env.OIDC_SCOPE) : process.env.OIDC_SCOPE ? JSON.stringify(process.env.OIDC_SCOPE) : JSON.stringify('openid profile email'),
        // Public path for OIDC redirect URIs (matches output.publicPath)
        '__PUBLIC_PATH__': JSON.stringify(PUBLIC_PATH),
      })
    ]
  };
};
