import { Game } from './scenes/Game';
import { MainMenu } from './scenes/MainMenu';
import { Preloader } from './scenes/Preloader';
import { PauseMenu } from './scenes/PauseMenu';
import { CharacterSelection } from './scenes/CharacterSelection';
import './ui.js'; // Import UI controls

const config = {
    type: Phaser.AUTO,
    width: 1024,
    height: 768,
    parent: 'game-container',
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    },
    scene: [
        Preloader,
        MainMenu,
        CharacterSelection,
        Game,
        PauseMenu
    ],
    physics: {
        default: "arcade",
        arcade: {
            gravity: { y: 0 },
        },
    },
};

const phaserGame = new Phaser.Game(config);

// Expose the game instance on window and disable default keyboard/input capture
window.game = phaserGame;

// Disable Phaser capture of keyboard inputs until simulator is launched
phaserGame.events.once('ready', () => {
    if (phaserGame.input) {
        phaserGame.input.enabled = false;
        if (phaserGame.input.keyboard) {
            phaserGame.input.keyboard.enabled = false;
        }
    }
});

export default phaserGame;
