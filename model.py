from tensorflow.keras.applications import VGG16
from tensorflow.keras.layers import Dense, Flatten
from tensorflow.keras.models import Model
from tensorflow.keras.preprocessing.image import ImageDataGenerator

def create_model():
    # Load pre-trained VGG16 model without top layers
    base_model = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    
    # Add custom layers
    x = base_model.output
    x = Flatten()(x)
    x = Dense(512, activation='relu')(x)
    predictions = Dense(2, activation='softmax')(x)  # Two classes: GPU and CPU
    
    # Create the final model
    model = Model(inputs=base_model.input, outputs=predictions)
    
    # Freeze the base model layers
    for layer in base_model.layers:
        layer.trainable = False
    
    # Compile the model
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    
    return model

def train_and_save_model():
    # Data augmentation and preprocessing
    train_datagen = ImageDataGenerator(rescale=1./255, validation_split=0.2)
    
    # Load training and validation data
    train_data = train_datagen.flow_from_directory(
        'dataset/',  # Path to dataset
        target_size=(224, 224),
        batch_size=32,
        class_mode='categorical',
        subset='training'
    )

    val_data = train_datagen.flow_from_directory(
        'dataset/',  # Path to dataset
        target_size=(224, 224),
        batch_size=32,
        class_mode='categorical',
        subset='validation'
    )
    
    # Create and train the model
    model = create_model()
    model.fit(train_data, validation_data=val_data, epochs=10)
    
    # Save the model
    model.save('model/product_model.h5')
    print("Model saved successfully!")

# Call this function to train and save the model
if __name__ == "__main__":
    train_and_save_model()