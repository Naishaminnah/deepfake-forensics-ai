import torchvision.transforms as T


# ---------------------------------------------------
# FAST + ACCURATE (recommended for 128px training)
# ---------------------------------------------------
def get_gan_transforms_fast(image_size: int):
    """
    Fast augmentations with light distortions.
    These preserve GAN fingerprint features while improving generalization.
    Best for: high speed + high accuracy.
    """
    return T.Compose([
        T.Resize((image_size, image_size)),

        # --- Light random augmentations ---
        T.RandomHorizontalFlip(0.5),
        T.RandomApply([
            T.ColorJitter(
                brightness=0.10,
                contrast=0.10,
                saturation=0.10,
                hue=0.02
            )
        ], p=0.3),

        # slight geometric distortions
        T.RandomRotation(10),
        T.RandomAffine(
            degrees=0,
            translate=(0.05, 0.05),
            scale=(0.95, 1.05)
        ),

        T.ToTensor(),

        # Standard ImageNet normalization
        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])


# ---------------------------------------------------
# MAXIMUM ACCURACY MODE (heavier augmentations)
# ---------------------------------------------------
def get_gan_transforms_heavy(image_size: int):
    """
    Strong augmentations for maximum robustness.
    Best for: highest accuracy when you have enough time.
    """
    return T.Compose([
        T.Resize((image_size, image_size)),

        # --- Strong augmentations ---
        T.RandomHorizontalFlip(0.5),
        T.RandomApply([
            T.ColorJitter(
                brightness=0.20,
                contrast=0.20,
                saturation=0.20,
                hue=0.03
            )
        ], p=0.6),

        T.RandomRotation(20),
        T.RandomPerspective(distortion_scale=0.4, p=0.4),

        T.RandomAffine(
            degrees=10,
            translate=(0.10, 0.10),
            scale=(0.90, 1.10),
            shear=5
        ),

        T.ToTensor(),

        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])


# ---------------------------------------------------
# VALIDATION / TEST TRANSFORMS (NO AUGMENTATION)
# ---------------------------------------------------
def get_gan_transforms_test_fast(image_size: int):
    """
    Test/validation transforms must NOT include any augmentation.
    """
    return T.Compose([
        T.Resize((image_size, image_size)),
        T.ToTensor(),
        T.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])
