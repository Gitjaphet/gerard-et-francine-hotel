-- Exécuté par l'image PostgreSQL au premier démarrage, quand le volume est vide.
-- La base de test est séparée de la base de développement : les tests la vident en permanence.
CREATE DATABASE hotel_test;
