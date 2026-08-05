const fs = require('fs');
const path = require('path');

module.exports = {
  parse: function(source) {
    return { ast: null, errors: ['Use WASM build for full parsing'] };
  },
  wasmPath: path.join(__dirname, 'wasm_parser_bg.wasm')
};
