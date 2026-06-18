class Character {
  constructor(scene, config) {
    this.scene = scene;
    this.id = config.id;
    this.name = config.name;
    this.spawnPoint = config.spawnPoint;
    this.atlas = config.atlas;
    this.defaultFrame = `${this.id}-${config.defaultDirection || 'front'}`;
    this.defaultMessage = config.defaultMessage;
    
    this.isRoaming = config.canRoam !== false; 
    this.moveSpeed = config.moveSpeed || 60;
    this.movementTimer = null;
    this.currentDirection = null;
    this.moveDuration = 0;
    this.pauseDuration = 0;
    this.roamRadius = config.roamRadius || 200; 
    this.pauseChance = config.pauseChance || 0.2; 
    this.directionChangeChance = config.directionChangeChance || 0.3;

    this.sprite = this.scene.physics.add
      .sprite(this.spawnPoint.x, this.spawnPoint.y, this.atlas, this.defaultFrame);
      
    if (config.scale) {
      this.sprite.setScale(config.scale);
    }
    
    this.sprite.setSize(30, 40)
      .setOffset(0, 0)
      .setImmovable(true);

    this.scene.physics.add.collider(this.sprite, config.worldLayer);
    
    this.createAnimations();
    this.createNameLabel();
    this.createEmotionBubble();
    
    if (this.isRoaming) {
      this.startRoaming();
    }
  }
  
  createAnimations() {
    const anims = this.scene.anims;
    const directions = ['left', 'right', 'front', 'back'];
    
    directions.forEach(direction => {
      const animKey = `${this.id}-${direction}-walk`;
      
      if (!anims.exists(animKey)) {
        anims.create({
          key: animKey,
          frames: anims.generateFrameNames(this.atlas, {
            prefix: `${this.id}-${direction}-walk-`,
            end: 8,
            zeroPad: 4,
          }),
          frameRate: 10,
          repeat: -1,
        });
      }
    });
  }
  
  facePlayer(player) {
    const dx = player.x - this.sprite.x;
    const dy = player.y - this.sprite.y;
    
    if (Math.abs(dx) > Math.abs(dy)) {
      this.sprite.setTexture(this.atlas, `${this.id}-${dx < 0 ? 'left' : 'right'}`);
    } else {
      this.sprite.setTexture(this.atlas, `${this.id}-${dy < 0 ? 'back' : 'front'}`);
    }
  }
  
  distanceToPlayer(player) {
    return Phaser.Math.Distance.Between(
      player.x, player.y,
      this.sprite.x, this.sprite.y
    );
  }
  
  isPlayerNearby(player, distance = 55) {
    return this.distanceToPlayer(player) < distance;
  }
  
  startRoaming() {
    this.chooseNewDirection();
  }
  
  chooseNewDirection() {
    if (this.movementTimer) {
      this.scene.time.removeEvent(this.movementTimer);
    }
    
    if (Math.random() < 0.75) { 
      const directions = ['left', 'right', 'up', 'down'];
      this.currentDirection = directions[Math.floor(Math.random() * directions.length)];
      
      const animKey = `${this.id}-${this.getDirectionFromMovement()}-walk`;
      if (this.scene.anims.exists(animKey)) {
        this.sprite.anims.play(animKey);
      } else {
        this.sprite.setTexture(this.atlas, `${this.id}-${this.getDirectionFromMovement()}`);
      }
      
      this.moveDuration = Phaser.Math.Between(1500, 4000);
      this.movementTimer = this.scene.time.delayedCall(this.moveDuration, () => {
        this.sprite.body.setVelocity(0);
        this.chooseNewDirection();
      });
    } else {
      this.currentDirection = null;
      this.sprite.anims.stop();
      
      const direction = ['front', 'back', 'left', 'right'][Math.floor(Math.random() * 4)];
      this.sprite.setTexture(this.atlas, `${this.id}-${direction}`);
      
      this.pauseDuration = Phaser.Math.Between(500, 2000);
      this.movementTimer = this.scene.time.delayedCall(this.pauseDuration, () => {
        this.chooseNewDirection();
      });
    }
  }
  
  getDirectionFromMovement() {
    switch(this.currentDirection) {
      case 'left': return 'left';
      case 'right': return 'right';
      case 'up': return 'back';
      case 'down': return 'front';
      default: return 'front';
    }
  }
  
  moveInCurrentDirection() {
    if (!this.currentDirection) return;
    
    const previousPosition = { x: this.sprite.x, y: this.sprite.y };
    
    this.sprite.body.setVelocity(0, 0); 
    
    switch(this.currentDirection) {
      case 'left':
        this.sprite.body.setVelocityX(-this.moveSpeed);
        break;
      case 'right':
        this.sprite.body.setVelocityX(this.moveSpeed);
        break;
      case 'up':
        this.sprite.body.setVelocityY(-this.moveSpeed);
        break;
      case 'down':
        this.sprite.body.setVelocityY(this.moveSpeed);
        break;
    }
    
    if (!this.stuckCheckTimer) {
      this.stuckCheckTimer = this.scene.time.addEvent({
        delay: 500,
        callback: () => {
          const distMoved = Phaser.Math.Distance.Between(
            previousPosition.x, previousPosition.y,
            this.sprite.x, this.sprite.y
          );
          if (distMoved < 5 && this.currentDirection) {
            // The NPC is stuck! We need to choose a new direction
            this.chooseNewDirection();
          }
          this.stuckCheckTimer = null;
        },
        callbackScope: this,
        loop: false
      });
    }
    
    // Check if we're moving too far from spawn point
    const distanceFromSpawn = Phaser.Math.Distance.Between(
      this.sprite.x, this.sprite.y,
      this.spawnPoint.x, this.spawnPoint.y
    );
    
    if (distanceFromSpawn > this.roamRadius) {
      // Turn around and head back toward spawn point
      this.sprite.body.setVelocity(0);
      
      const dx = this.spawnPoint.x - this.sprite.x;
      const dy = this.spawnPoint.y - this.sprite.y;
      
      if (Math.abs(dx) > Math.abs(dy)) {
        this.currentDirection = dx > 0 ? 'right' : 'left';
      } else {
        this.currentDirection = dy > 0 ? 'down' : 'up';
      }
      
      const animKey = `${this.id}-${this.getDirectionFromMovement()}-walk`;
      if (this.scene.anims.exists(animKey)) {
        this.sprite.anims.play(animKey);
      } else {
        this.sprite.setTexture(this.atlas, `${this.id}-${this.getDirectionFromMovement()}`);
      }
      
      // Add a timer to force direction change if they get stuck
      if (this.movementTimer) {
        this.scene.time.removeEvent(this.movementTimer);
      }
      
      this.movementTimer = this.scene.time.delayedCall(1500, () => {
        this.chooseNewDirection();
      });
    }
  }
  
  update(player, isInDialogue) {
    // If in dialogue with the player, stop moving and face them
    if (isInDialogue && this.isPlayerNearby(player)) {
      this.sprite.body.setVelocity(0);
      this.facePlayer(player);
      this.sprite.anims.stop();
      
      // Pause roaming while in dialogue
      if (this.movementTimer) {
        this.scene.time.removeEvent(this.movementTimer);
        this.movementTimer = null;
      }
    } 
    else if (this.isRoaming) {
      if (!this.movementTimer) {
        this.startRoaming();
      }
      
      this.moveInCurrentDirection();
    } else {
      this.sprite.body.setVelocity(0);
    }
    
    // Update name label position
    if (this.nameLabel) {
      this.nameLabel.x = this.sprite.x;
      const offset = (this.sprite.displayHeight || this.sprite.height) / 2;
      this.nameLabel.y = this.sprite.y - offset - 10;
    }

    if (this.emotionContainer) {
      this.emotionContainer.x = this.sprite.x + 15;
      const offset = (this.sprite.displayHeight || this.sprite.height) / 2;
      this.emotionContainer.y = this.sprite.y - offset - 20;
    }
  }

  get position() {
    return {
      x: this.sprite.x,
      y: this.sprite.y
    };
  }
  
  get body() {
    return this.sprite;
  }

  createNameLabel() {
    this.nameLabel = this.scene.add.text(0, 0, this.name, {
      font: "14px Arial",
      fill: "#ffffff",
      backgroundColor: "#000000",
      padding: { x: 4, y: 2 },
      align: "center"
    });
    this.nameLabel.setOrigin(0.5, 1);
    this.nameLabel.setDepth(20);
    this.updateNameLabelPosition();
  }

  updateNameLabelPosition() {
    if (this.nameLabel && this.sprite) {
      const offset = (this.sprite.displayHeight || this.sprite.height) / 2;
      this.nameLabel.setPosition(
        this.sprite.x,
        this.sprite.y - offset - 10
      );
    }
    if (this.emotionContainer && this.sprite) {
      const offset = (this.sprite.displayHeight || this.sprite.height) / 2;
      this.emotionContainer.setPosition(
        this.sprite.x + 15,
        this.sprite.y - offset - 20
      );
    }
  }

  createEmotionBubble() {
    this.emotionContainer = this.scene.add.container(0, 0);
    this.emotionContainer.setDepth(20);

    this.emotionBubble = this.scene.add.graphics();
    this.emotionBubble.fillStyle(0xffffff, 0.9);
    this.emotionBubble.fillRoundedRect(-15, -15, 30, 30, 8);
    this.emotionBubble.lineStyle(2, 0x000000, 1);
    this.emotionBubble.strokeRoundedRect(-15, -15, 30, 30, 8);
    
    // Add a little tail to the bubble
    this.emotionBubble.fillStyle(0xffffff, 0.9);
    this.emotionBubble.fillTriangle(-5, 12, 5, 12, -10, 22);
    this.emotionBubble.lineStyle(2, 0x000000, 1);
    this.emotionBubble.strokeTriangle(-5, 12, 5, 12, -10, 22);

    this.emotionText = this.scene.add.text(0, 0, '', {
      font: "16px Arial",
      align: "center"
    }).setOrigin(0.5);

    this.emotionContainer.add([this.emotionBubble, this.emotionText]);
    this.emotionContainer.setVisible(false);

    // List of possible emotions
    this.emotions = ['😀', '🤔', '😴', '😠', '😢', '😤', '💡', '💬', '💭', '😲', '🙃'];
    
    this.startEmotionTimer();
    this.updateNameLabelPosition();
  }

  startEmotionTimer() {
    const delay = Phaser.Math.Between(4000, 12000);
    this.emotionTimer = this.scene.time.delayedCall(delay, () => {
      this.showRandomEmotion();
    });
  }

  showRandomEmotion() {
    if (!this.emotionContainer || !this.sprite) return;

    const emotion = Phaser.Utils.Array.GetRandom(this.emotions);
    this.emotionText.setText(emotion);
    this.emotionContainer.setVisible(true);

    const hideDelay = Phaser.Math.Between(2000, 4000);
    this.scene.time.delayedCall(hideDelay, () => {
      if (this.emotionContainer) {
          this.emotionContainer.setVisible(false);
      }
      this.startEmotionTimer();
    });
  }

  destroy() {
    if (this.movementTimer) {
      this.scene.time.removeEvent(this.movementTimer);
    }
    if (this.stuckCheckTimer) {
      this.scene.time.removeEvent(this.stuckCheckTimer);
    }
    if (this.emotionTimer) {
      this.scene.time.removeEvent(this.emotionTimer);
    }
    
    if (this.emotionContainer) {
      this.emotionContainer.destroy();
    }
    this.nameLabel.destroy();
    this.sprite.destroy();
  }
}

export default Character; 
