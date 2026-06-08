import { Scene } from 'phaser';

export class CharacterSelection extends Scene {
    constructor() {
        super('CharacterSelection');
    }

    create() {
        this.add.image(0, 0, 'background').setOrigin(0, 0);
        
        // Add a dark overlay
        const overlay = this.add.graphics();
        overlay.fillStyle(0x000000, 0.7);
        overlay.fillRect(0, 0, this.cameras.main.width, this.cameras.main.height);

        const centerX = this.cameras.main.width / 2;
        const centerY = this.cameras.main.height / 2;

        this.add.text(centerX, 150, 'CHOOSE YOUR CHARACTER', {
            fontSize: '40px',
            fontFamily: 'Arial',
            color: '#ffffff',
            fontStyle: 'bold'
        }).setOrigin(0.5);

        // Display Boy Option (Paul)
        const boySprite = this.add.sprite(centerX - 200, centerY - 50, 'paul', 'paul-front').setScale(2);
        this.createButton(centerX - 200, centerY + 100, 'Play as Boy', () => {
            this.selectCharacter('paul');
        });

        // Display Girl Option (Sophia)
        const girlSprite = this.add.sprite(centerX + 200, centerY - 50, 'sophia', 'sophia-front').setScale(2);
        this.createButton(centerX + 200, centerY + 100, 'Play as Girl', () => {
            this.selectCharacter('sophia');
        });

        // Back button
        this.createButton(centerX, this.cameras.main.height - 100, 'Back to Menu', () => {
            this.scene.start('MainMenu');
        });
    }

    selectCharacter(spriteKey) {
        let name = window.prompt("Enter your character's name:", "Player");
        if (!name || name.trim() === "") {
            name = "Player";
        }

        this.scene.start('Game', {
            playerName: name.trim(),
            playerSprite: spriteKey
        });
    }

    createButton(x, y, text, callback) {
        const buttonWidth = 250;
        const buttonHeight = 60;
        const cornerRadius = 15;

        const shadow = this.add.graphics();
        shadow.fillStyle(0x444444, 1);
        shadow.fillRoundedRect(x - buttonWidth / 2 + 4, y - buttonHeight / 2 + 4, buttonWidth, buttonHeight, cornerRadius);

        const button = this.add.graphics();
        button.fillStyle(0xffffff, 1);
        button.fillRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
        button.setInteractive(
            new Phaser.Geom.Rectangle(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight),
            Phaser.Geom.Rectangle.Contains
        );

        const buttonText = this.add.text(x, y, text, {
            fontSize: '24px',
            fontFamily: 'Arial',
            color: '#000000',
            fontStyle: 'bold'
        }).setOrigin(0.5);

        button.on('pointerover', () => {
            button.clear();
            button.fillStyle(0x87CEEB, 1);
            button.fillRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
            buttonText.y -= 2;
        });

        button.on('pointerout', () => {
            button.clear();
            button.fillStyle(0xffffff, 1);
            button.fillRoundedRect(x - buttonWidth / 2, y - buttonHeight / 2, buttonWidth, buttonHeight, cornerRadius);
            buttonText.y += 2;
        });

        button.on('pointerdown', callback);
    }
}
