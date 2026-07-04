// Standalone Metro config. apps/native is NOT part of the root npm workspace
// (root workspaces = apps/web + packages/*), so default resolution is correct.
const { getDefaultConfig } = require('expo/metro-config')

const config = getDefaultConfig(__dirname)

module.exports = config
