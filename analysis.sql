-- QUERY hourly_demand
SELECT workingday, hour, COUNT(*) AS observed_hours,
       ROUND(AVG(total), 2) AS avg_rentals_per_observed_hour,
       SUM(total) AS total_rentals
FROM rentals
GROUP BY workingday, hour
ORDER BY workingday, hour;

-- QUERY monthly_demand
SELECT substr(date, 1, 7) AS month, COUNT(*) AS observed_hours,
       SUM(total) AS total_rentals, ROUND(AVG(total), 2) AS avg_rentals_per_observed_hour
FROM rentals
GROUP BY month
ORDER BY month;
