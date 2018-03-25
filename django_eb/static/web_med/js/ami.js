export * from './cameras/cameras.js';
export * from './controls/controls.js';
export * from './core/core.js';
export * from './geometries/geometries.js';
export * from './helpers/helpers.js';
export * from './loaders/loaders.js';
export * from './models/models.js';
export * from './parsers/parsers.js';
export * from './presets/presets.js';
export * from './shaders/shaders.js';
export * from './widgets/widgets.js';

const pckg = require('../package.json');
window.console.log(`AMI ${pckg.version} ( ThreeJS ${pckg.config.threeVersion})`);