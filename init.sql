-- Création de la table des tâches
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    done BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Données de test initiales
INSERT INTO tasks (title) VALUES ('Configurer Docker Compose');
INSERT INTO tasks (title) VALUES ('Tester l''API Flask');